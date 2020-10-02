import json
from unittest.mock import patch
from django.contrib.auth.models import User
from rest_framework import status
from cjwkernel.tests.util import arrow_table
from cjwkernel.types import RenderResult
from cjwstate import rabbitmq
from cjwstate.rendercache import cache_render_result
from cjwstate.models import Workflow
from cjwstate.models.commands import InitWorkflowCommand
from cjwstate.tests.utils import (
    DbTestCaseWithModuleRegistryAndMockKernel,
    create_module_zipfile,
)
from server.views.workflows import Index, render_workflow


_original_workflow_duplicate_anonymous = Workflow.duplicate_anonymous


async def async_noop(*args, **kwargs):
    pass


@patch("cjwstate.commands.websockets_notify", async_noop)
class WorkflowViewTests(DbTestCaseWithModuleRegistryAndMockKernel):
    def setUp(self):
        super().setUp()

        self.queue_render_patcher = patch.object(rabbitmq, "queue_render")
        self.queue_render = self.queue_render_patcher.start()
        self.queue_render.side_effect = async_noop

        self.log_patcher = patch("server.utils.log_user_event_from_request")
        self.log_patch = self.log_patcher.start()

        self.user = User.objects.create(
            username="user", email="user@example.com", password="password"
        )

        self.workflow1 = Workflow.create_and_init(name="Workflow 1", owner=self.user)
        self.delta = self.workflow1.last_delta
        self.tab1 = self.workflow1.tabs.first()
        self.module_zipfile1 = create_module_zipfile("module1")

        # Add another user, with one public and one private workflow
        self.otheruser = User.objects.create(
            username="user2", email="user2@example.com", password="password"
        )

    def tearDown(self):
        self.log_patcher.stop()
        self.queue_render_patcher.stop()
        super().tearDown()

    # --- Workflow list ---
    def test_index_get(self):
        # set dates to test reverse chron ordering
        self.workflow1.creation_date = "2010-10-20 1:23Z"
        self.workflow1.save()
        self.workflow2 = Workflow.create_and_init(
            name="Workflow 2", owner=self.user, creation_date="2015-09-18 2:34Z"
        )

        self.client.force_login(self.user)
        response = self.client.get("/workflows/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        workflows = response.context_data["initState"]["workflows"]
        # should not pick up other user's workflows, even public ones
        self.assertEqual(
            len(workflows["owned"])
            + len(workflows["shared"])
            + len(workflows["templates"]),
            2,
        )

        self.assertEqual(workflows["owned"][0]["name"], "Workflow 2")
        self.assertEqual(workflows["owned"][0]["id"], self.workflow2.id)
        self.assertEqual(workflows["owned"][0]["public"], self.workflow1.public)
        self.assertEqual(workflows["owned"][0]["read_only"], False)  # user is owner
        self.assertEqual(workflows["owned"][0]["is_owner"], True)  # user is owner
        self.assertIsNotNone(workflows["owned"][0]["last_update"])
        self.assertEqual(workflows["owned"][0]["owner_name"], "user@example.com")

        self.assertEqual(workflows["owned"][1]["name"], "Workflow 1")
        self.assertEqual(workflows["owned"][1]["id"], self.workflow1.id)

    def test_index_include_example_in_all_users_workflow_lists(self):
        self.other_workflow_public = Workflow.create_and_init(
            name="Other workflow public",
            owner=self.otheruser,
            public=True,
            example=True,
            in_all_users_workflow_lists=True,
        )
        self.workflow2 = Workflow.create_and_init(owner=self.user)

        self.client.force_login(self.user)
        response = self.client.get("/workflows/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        workflows = response.context_data["initState"]["workflows"]
        self.assertEqual(len(workflows["owned"]), 2)
        self.assertEqual(len(workflows["templates"]), 1)

    def test_index_exclude_example_not_in_all_users_lists(self):
        self.other_workflow_public = Workflow.create_and_init(
            name="Other workflow public",
            owner=self.otheruser,
            public=True,
            example=True,
            in_all_users_workflow_lists=False,
        )
        self.workflow2 = Workflow.create_and_init(owner=self.user)

        self.client.force_login(self.user)
        response = self.client.get("/workflows/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        workflows = response.context_data["initState"]["workflows"]
        self.assertEqual(len(workflows["owned"]), 2)
        self.assertEqual(len(workflows["templates"]), 0)

    def test_index_exclude_lesson(self):
        self.workflow1.lesson_slug = "some-lesson"
        self.workflow1.save()
        self.workflow2 = Workflow.create_and_init(owner=self.user)

        self.client.force_login(self.user)
        response = self.client.get("/workflows/")
        workflows = response.context_data["initState"]["workflows"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(workflows["owned"]), 1)

    def test_index_post(self):
        self.client.force_login(self.user)
        response = self.client.post("/workflows/")
        workflow = Workflow.objects.get(name="Untitled Workflow")  # or crash
        self.assertRedirects(response, "/workflows/%d/" % workflow.id)

    # --- Workflow ---
    # This is the HTTP response, as opposed to the API
    def test_workflow_view(self):
        # View own non-public workflow
        self.client.force_login(self.user)
        response = self.client.get("/workflows/%d/" % self.workflow1.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_workflow_view_update_last_viewed_at(self):
        # View own non-public workflow
        self.client.force_login(self.user)
        date1 = self.workflow1.last_viewed_at
        self.client.get("/workflows/%d/" % self.workflow1.id)
        self.workflow1.refresh_from_db()
        date2 = self.workflow1.last_viewed_at
        self.assertGreater(date2, date1)

    @patch("cjwstate.models.Workflow.cooperative_lock")
    def test_workflow_view_race_delete_after_auth(self, lock):
        # cooperative_lock() is called _after_ auth. (Auth is optimized to be
        # quick, which means no cooperative_lock().) Assume make_init_state()
        # calls it, for serialization. Well, the Workflow may be deleted after
        # auth and before make_init_state().
        lock.side_effect = Workflow.DoesNotExist
        self.client.force_login(self.user)
        response = self.client.get("/workflows/%d/" % self.workflow1.id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_workflow_view_triggers_render_if_stale_cache(self):
        step = self.tab1.steps.create(
            order=0,
            slug="step-1",
            last_relevant_delta_id=self.delta.id,
            cached_render_result_delta_id=self.delta.id,  # stale
        )
        # Cache a result
        cache_render_result(
            self.workflow1, step, self.delta.id, RenderResult(arrow_table({"A": ["a"]}))
        )
        # Make the cached result stale. (The view will actually send the
        # stale-result metadata to the client. That's why we cached it.)
        delta2 = InitWorkflowCommand.create(self.workflow1)
        step.last_relevant_delta_id = delta2.id
        step.save(update_fields=["last_relevant_delta_id"])
        self.client.force_login(self.user)
        self.client.get("/workflows/%d/" % self.workflow1.id)
        self.queue_render.assert_called_with(self.workflow1.id, delta2.id)

    def test_workflow_view_triggers_render_if_no_cache(self):
        self.tab1.steps.create(
            order=0,
            slug="step-1",
            last_relevant_delta_id=self.delta.id,
            cached_render_result_delta_id=None,
        )
        self.client.force_login(self.user)
        self.client.get("/workflows/%d/" % self.workflow1.id)
        self.queue_render.assert_called_with(self.workflow1.id, self.delta.id)

    def test_workflow_view_missing_404(self):
        # 404 with bad id
        self.client.force_login(self.user)
        response = self.client.get("/workflows/%d/" % 999_999)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_workflow_view_shared(self):
        public_workflow = Workflow.create_and_init(
            name="Other workflow public", owner=self.otheruser, public=True
        )
        # View someone else's public workflow
        self.client.force_login(self.user)
        response = self.client.get("/workflows/%d/" % public_workflow.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_workflow_view_unauthorized_403(self):
        # 403 viewing someone else' private workflow (don't 404 as sometimes
        # users try to share workflows by sharing the URL without first making
        # them public, and we need to help them debug that case)
        self.client.force_login(self.otheruser)
        response = self.client.get("/workflows/%d/" % self.workflow1.id)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch.dict(
        "os.environ",
        {
            "CJW_INTERCOM_APP_ID": "myIntercomId",
            "CJW_GOOGLE_ANALYTICS": "myGaId",
            "CJW_HEAP_ANALYTICS_ID": "myHeapId",
        },
    )
    def test_workflow_init_state(self):
        self.client.force_login(self.user)
        # checks to make sure the right initial data is embedded in the HTML (username etc.)
        response = self.client.get(
            "/workflows/%d/" % self.workflow1.id
        )  # need trailing slash or 301
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertContains(response, '"loggedInUser"')
        self.assertContains(response, self.user.email)

        self.assertContains(response, '"workflow"')
        self.assertContains(response, '"modules"')

        self.assertContains(response, "myIntercomId")
        self.assertContains(response, "myGaId")
        self.assertContains(response, "myHeapId")

    def test_workflow_acl_reader_reads_but_does_not_write(self):
        self.workflow1.acl.create(email="user2@example.com", can_edit=False)
        self.client.force_login(self.otheruser)

        # GET: works
        response = self.client.get(f"/workflows/{self.workflow1.id}/")
        self.assertEqual(response.status_code, 200)

        # POST: does not work
        response = self.client.post(
            f"/api/workflows/{self.workflow1.id}/",
            data='{"public":true}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_workflow_acl_writer_reads_and_writes(self):
        self.workflow1.acl.create(email="user2@example.com", can_edit=True)
        self.client.force_login(self.otheruser)

        # GET: works
        response = self.client.get(f"/workflows/{self.workflow1.id}/")
        self.assertEqual(response.status_code, 200)

        # POST: works
        response = self.client.post(
            f"/api/workflows/{self.workflow1.id}/",
            data='{"public":true}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 204)

    def test_workflow_anonymous_user(self):
        # Looking at example workflow as anonymous should create a new workflow
        public_workflow = Workflow.create_and_init(
            name="Other workflow public",
            owner=self.otheruser,
            public=True,
            example=True,
        )

        # don't log in
        response = self.client.get("/workflows/%d/" % public_workflow.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(
            Workflow.objects.filter(owner=None).count(), 1
        )  # should have duplicated the  wf with this API call

        # Ensure the anonymous users can't access the Python module
        self.assertNotContains(response, '"pythoncode"')

    @patch.object(Workflow, "duplicate_anonymous")
    def test_workflow_prevent_race_creating_two_demos_per_user(
        self, duplicate_anonymous
    ):
        public_workflow = Workflow.create_and_init(
            name="Other workflow public",
            owner=self.otheruser,
            public=True,
            example=True,
        )

        dup_result: Workflow = None

        def racing_duplicate_anonymous(session_key):
            # Let's pretend two requests are doing this simultaneously...
            #
            # The _other_ thread "won": its duplication will proceed as
            # planned.
            nonlocal dup_result
            dup_result = _original_workflow_duplicate_anonymous(
                public_workflow, session_key
            )

            # Now, _our_ thread should run into a problem because we're trying
            # to duplicate onto a session key that's already duplicated.
            return _original_workflow_duplicate_anonymous(public_workflow, session_key)

        duplicate_anonymous.side_effect = racing_duplicate_anonymous

        self.client.session._session_key = "session-b"
        response = self.client.get("/workflows/%d/" % public_workflow.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Assert there is only _one_ extra workflow.
        self.assertEqual(Workflow.objects.filter(owner=None).count(), 1)
        # This request "lost" the race; assert it has the same workflow as the
        # request that "won" the race.
        self.assertEqual(
            response.context_data["initState"]["workflow"]["id"], dup_result.id
        )

    def test_workflow_duplicate_view(self):
        old_ids = [
            w.id for w in Workflow.objects.all()
        ]  # list of all current workflow ids
        self.client.force_login(self.user)
        response = self.client.post("/api/workflows/%d/duplicate" % self.workflow1.id)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = json.loads(response.content)
        self.assertFalse(data["id"] in old_ids)  # created at entirely new id
        self.assertEqual(data["name"], "Copy of Workflow 1")
        self.assertTrue(Workflow.objects.filter(pk=data["id"]).exists())

    def test_workflow_duplicate_missing_gives_404(self):
        # Ensure 404 with bad id
        self.client.force_login(self.user)
        response = self.client.post("/api/workflows/99999/duplicate")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_workflow_duplicate_restricted_gives_403(self):
        # Ensure 403 when another user tries to clone private workflow
        self.client.force_login(self.user)
        self.assertFalse(self.workflow1.public)
        self.client.force_login(self.otheruser)
        response = self.client.post("/api/workflows/%d/duplicate" % self.workflow1.id)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_workflow_duplicate_public(self):
        self.workflow1.public = True
        self.workflow1.save()
        self.client.force_login(self.otheruser)
        response = self.client.post("/api/workflows/%d/duplicate" % self.workflow1.id)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_workflow_delete(self):
        pk_workflow = self.workflow1.id
        self.client.force_login(self.user)
        response = self.client.delete("/api/workflows/%d/" % pk_workflow)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Workflow.objects.filter(name="Workflow 1").count(), 0)

    def test_workflow_delete_missing_is_404(self):
        # It's okay because the thing that leads to this might be a user
        # double-clicking on a "delete" button.
        count_before = Workflow.objects.count()
        pk_workflow = self.workflow1.id + 999  # does not exist
        self.client.force_login(self.user)
        response = self.client.delete("/api/workflows/%d/" % pk_workflow)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(Workflow.objects.count(), count_before)

    def test_workflow_delete_unauthorized_is_403(self):
        count_before = Workflow.objects.count()
        pk_workflow = self.workflow1.id
        self.client.force_login(self.otheruser)  # has no permission
        response = self.client.delete("/api/workflows/%d/" % pk_workflow)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Workflow.objects.count(), count_before)

    def test_workflow_post_public(self):
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/workflows/%d" % self.workflow1.id,
            {"public": True},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.workflow1.refresh_from_db()
        self.assertEqual(self.workflow1.public, True)

    def test_workflow_post_public_unauthorized_is_403(self):
        self.client.force_login(self.otheruser)
        response = self.client.post(
            "/api/workflows/%d" % self.workflow1.id,
            {"public": True},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.workflow1.refresh_from_db()
        self.assertEqual(self.workflow1.public, False)
