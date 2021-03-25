import json
from http import HTTPStatus as status
from unittest.mock import patch

from django.contrib.auth.models import User

from cjwkernel.tests.util import arrow_table
from cjwkernel.types import RenderResult
from cjwstate import rabbitmq
from cjwstate.models import Workflow
from cjwstate.models.fields import Role
from cjwstate.rendercache import cache_render_result
from cjwstate.tests.utils import DbTestCase
from server.views.workflows import Index, render_workflow

_original_workflow_duplicate_anonymous = Workflow.duplicate_anonymous


async def async_noop(*args, **kwargs):
    pass


def create_user(username: str, email: str):
    return User.objects.create(username=username, email=email)


class WorkflowListTest(DbTestCase):
    def setUp(self):
        super().setUp()

        self.user = create_user("user", "user@example.com")
        self.other_user = create_user("other_user", "other_user@example.com")

    def test_index_get(self):
        # set dates to test reverse chron ordering
        workflow1 = Workflow.create_and_init(
            name="Workflow 1", owner=self.user, updated_at="2010-10-20T1:23"
        )
        workflow2 = Workflow.create_and_init(
            name="Workflow 2", owner=self.user, updated_at="2015-09-18T2:34"
        )

        self.client.force_login(self.user)
        response = self.client.get("/workflows")
        self.assertEqual(response.status_code, status.OK)

        workflows = response.context_data["initState"]["workflows"]
        # should not pick up other user's workflows, even public ones
        self.assertEqual(len(workflows), 2)

        self.assertEqual(workflows[0]["name"], "Workflow 2")
        self.assertEqual(workflows[0]["id"], workflow2.id)
        self.assertEqual(workflows[0]["public"], workflow1.public)
        self.assertEqual(workflows[0]["read_only"], False)  # user is owner
        self.assertEqual(workflows[0]["is_owner"], True)  # user is owner
        self.assertIsNotNone(workflows[0]["last_update"])
        self.assertEqual(workflows[0]["owner_name"], "user@example.com")

        self.assertEqual(workflows[1]["name"], "Workflow 1")
        self.assertEqual(workflows[1]["id"], workflow1.id)

    def test_index_ignore_other_user_workflows(self):
        Workflow.create_and_init(name="Hers", owner=self.other_user)
        self.client.force_login(self.user)
        response = self.client.get("/workflows")
        self.assertEqual(response.context_data["initState"]["workflows"], [])

    def test_index_ignore_example(self):
        Workflow.create_and_init(
            name="Example",
            owner=self.other_user,
            public=True,
            example=True,
            in_all_users_workflow_lists=True,
        )
        self.client.force_login(self.user)
        response = self.client.get("/workflows")
        self.assertEqual(response.context_data["initState"]["workflows"], [])

    def test_index_ignore_lesson(self):
        Workflow.create_and_init(name="Hers", owner=self.user, lesson_slug="a-lesson")
        self.client.force_login(self.user)
        response = self.client.get("/workflows")
        self.assertEqual(response.context_data["initState"]["workflows"], [])

    def test_shared(self):
        workflow = Workflow.create_and_init(name="Hers", owner=self.other_user)
        workflow.acl.create(email=self.user.email, role=Role.VIEWER)
        self.client.force_login(self.user)
        response = self.client.get("/workflows/shared-with-me")
        self.assertEqual(
            [w["name"] for w in response.context_data["initState"]["workflows"]],
            ["Hers"],
        )

    def test_examples(self):
        Workflow.create_and_init(
            name="Example",
            owner=self.other_user,
            public=True,
            example=True,
            in_all_users_workflow_lists=True,
        )
        self.client.force_login(self.user)
        response = self.client.get("/workflows/examples")
        self.assertEqual(
            [w["name"] for w in response.context_data["initState"]["workflows"]],
            ["Example"],
        )

    def test_examples_ignore_when_not_in_all_users_workflow_lists(self):
        Workflow.create_and_init(
            name="Example",
            owner=self.other_user,
            public=True,
            example=True,
            in_all_users_workflow_lists=False,
        )
        self.client.force_login(self.user)
        response = self.client.get("/workflows/examples")
        self.assertEqual(response.context_data["initState"]["workflows"], [])


@patch("cjwstate.commands.websockets_notify", async_noop)
class WorkflowViewTests(DbTestCase):
    def setUp(self):
        super().setUp()

        self.queue_render_patcher = patch.object(rabbitmq, "queue_render")
        self.queue_render = self.queue_render_patcher.start()
        self.queue_render.side_effect = async_noop

        self.log_patcher = patch("server.utils.log_user_event_from_request")
        self.log_patch = self.log_patcher.start()

        self.user = create_user("user", "user@example.com")

        self.workflow1 = Workflow.create_and_init(name="Workflow 1", owner=self.user)
        self.tab1 = self.workflow1.tabs.first()

        # Add another user, with one public and one private workflow
        self.otheruser = create_user("user2", "user2@example.com")

    def tearDown(self):
        self.log_patcher.stop()
        self.queue_render_patcher.stop()
        super().tearDown()

    # --- Workflow list ---

    def test_index_post(self):
        self.client.force_login(self.user)
        response = self.client.post("/workflows")
        workflow = Workflow.objects.get(name="Untitled Workflow")  # or crash
        self.assertRedirects(response, "/workflows/%d/" % workflow.id)

    # --- Workflow ---
    # This is the HTTP response, as opposed to the API
    def test_workflow_view(self):
        # View own non-public workflow
        self.client.force_login(self.user)
        response = self.client.get("/workflows/%d/" % self.workflow1.id)
        self.assertEqual(response.status_code, status.OK)

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
        self.assertEqual(response.status_code, status.NOT_FOUND)

    def test_workflow_view_triggers_render_if_stale_cache(self):
        step = self.tab1.steps.create(
            order=0,
            slug="step-1",
            last_relevant_delta_id=1,
            cached_render_result_delta_id=1,
        )
        # Cache a result
        cache_render_result(
            self.workflow1,
            step,
            1,
            RenderResult(arrow_table({"A": ["a"]})),
        )
        step.last_relevant_delta_id = 2
        step.save(update_fields=["last_relevant_delta_id"])
        self.client.force_login(self.user)
        self.client.get("/workflows/%d/" % self.workflow1.id)
        self.queue_render.assert_called_with(
            self.workflow1.id, self.workflow1.last_delta_id
        )

    def test_workflow_view_triggers_render_if_no_cache(self):
        self.tab1.steps.create(
            order=0, slug="step-1", cached_render_result_delta_id=None
        )
        self.client.force_login(self.user)
        self.client.get("/workflows/%d/" % self.workflow1.id)
        self.queue_render.assert_called_with(
            self.workflow1.id, self.workflow1.last_delta_id
        )

    def test_workflow_view_missing_404(self):
        # 404 with bad id
        self.client.force_login(self.user)
        response = self.client.get("/workflows/%d/" % 999_999)
        self.assertEqual(response.status_code, status.NOT_FOUND)

    def test_workflow_view_shared(self):
        public_workflow = Workflow.create_and_init(
            name="Other workflow public", owner=self.otheruser, public=True
        )
        # View someone else's public workflow
        self.client.force_login(self.user)
        response = self.client.get("/workflows/%d/" % public_workflow.id)
        self.assertEqual(response.status_code, status.OK)

    def test_workflow_view_unauthorized_403(self):
        # 403 viewing someone else' private workflow (don't 404 as sometimes
        # users try to share workflows by sharing the URL without first making
        # them public, and we need to help them debug that case)
        self.client.force_login(self.otheruser)
        response = self.client.get("/workflows/%d/" % self.workflow1.id)
        self.assertEqual(response.status_code, status.FORBIDDEN)

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
        self.assertEqual(response.status_code, status.OK)

        self.assertContains(response, '"loggedInUser"')
        self.assertContains(response, self.user.email)

        self.assertContains(response, '"workflow"')
        self.assertContains(response, '"modules"')

        self.assertContains(response, "myIntercomId")
        self.assertContains(response, "myGaId")
        self.assertContains(response, "myHeapId")

    def test_workflow_acl_reader_reads_but_does_not_write(self):
        self.workflow1.acl.create(email="user2@example.com", role=Role.VIEWER)
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
        self.workflow1.acl.create(email="user2@example.com", role=Role.EDITOR)
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
        self.assertEqual(response.status_code, status.OK)

        self.assertEqual(
            Workflow.objects.filter(owner=None).count(), 1
        )  # should have duplicated the  wf with this API call

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
        self.assertEqual(response.status_code, status.OK)
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
        response = self.client.post("/workflows/%d/duplicate" % self.workflow1.id)
        self.assertEqual(response.status_code, status.CREATED)
        data = json.loads(response.content)
        self.assertFalse(data["id"] in old_ids)  # created at entirely new id
        self.assertEqual(data["name"], "Copy of Workflow 1")
        self.assertTrue(Workflow.objects.filter(pk=data["id"]).exists())

    def test_workflow_duplicate_missing_gives_404(self):
        # Ensure 404 with bad id
        self.client.force_login(self.user)
        response = self.client.post("/workflows/99999/duplicate")
        self.assertEqual(response.status_code, status.NOT_FOUND)

    def test_workflow_duplicate_secret(self):
        self.workflow1.public = False
        self.workflow1.secret_id = "wsecret"
        self.workflow1.save(update_fields=["public", "secret_id"])
        self.client.force_login(self.otheruser)
        response = self.client.post("/workflows/wsecret/duplicate")
        self.assertEqual(response.status_code, status.CREATED)

    def test_workflow_duplicate_restricted_gives_403(self):
        # Ensure 403 when another user tries to clone private workflow
        self.client.force_login(self.user)
        self.assertFalse(self.workflow1.public)
        self.client.force_login(self.otheruser)
        response = self.client.post("/workflows/%d/duplicate" % self.workflow1.id)
        self.assertEqual(response.status_code, status.FORBIDDEN)

    def test_workflow_duplicate_public(self):
        self.workflow1.public = True
        self.workflow1.save()
        self.client.force_login(self.otheruser)
        response = self.client.post("/workflows/%d/duplicate" % self.workflow1.id)
        self.assertEqual(response.status_code, status.CREATED)

    def test_workflow_delete(self):
        pk_workflow = self.workflow1.id
        self.client.force_login(self.user)
        response = self.client.delete("/api/workflows/%d/" % pk_workflow)
        self.assertEqual(response.status_code, status.NO_CONTENT)
        self.assertEqual(Workflow.objects.filter(name="Workflow 1").count(), 0)

    def test_workflow_delete_missing_is_404(self):
        # It's okay because the thing that leads to this might be a user
        # double-clicking on a "delete" button.
        count_before = Workflow.objects.count()
        pk_workflow = self.workflow1.id + 999  # does not exist
        self.client.force_login(self.user)
        response = self.client.delete("/api/workflows/%d/" % pk_workflow)
        self.assertEqual(response.status_code, status.NOT_FOUND)
        self.assertEqual(Workflow.objects.count(), count_before)

    def test_workflow_delete_unauthorized_is_403(self):
        count_before = Workflow.objects.count()
        pk_workflow = self.workflow1.id
        self.client.force_login(self.otheruser)  # has no permission
        response = self.client.delete("/api/workflows/%d/" % pk_workflow)
        self.assertEqual(response.status_code, status.FORBIDDEN)
        self.assertEqual(Workflow.objects.count(), count_before)

    def test_workflow_post_public(self):
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/workflows/%d" % self.workflow1.id,
            {"public": True},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.NO_CONTENT)
        self.workflow1.refresh_from_db()
        self.assertEqual(self.workflow1.public, True)

    def test_workflow_post_public_unauthorized_is_403(self):
        self.client.force_login(self.otheruser)
        response = self.client.post(
            "/api/workflows/%d" % self.workflow1.id,
            {"public": True},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.FORBIDDEN)
        self.workflow1.refresh_from_db()
        self.assertEqual(self.workflow1.public, False)


class SecretLinkTests(DbTestCase):
    def setUp(self):
        super().setUp()

        self.queue_render_patcher = patch.object(rabbitmq, "queue_render")
        self.queue_render = self.queue_render_patcher.start()
        self.queue_render.side_effect = async_noop

        self.log_patcher = patch("server.utils.log_user_event_from_request")
        self.log_patch = self.log_patcher.start()

        self.owner = create_user("owner", "owner@example.com")
        self.viewer = create_user("viewer", "viewer@example.com")
        self.report_viewer = create_user("report_viewer", "report_viewer@example.com")
        self.other_user = create_user("other_user", "other_user@example.com")

        self.workflow = Workflow.create_and_init(name="Workflow", owner=self.owner)
        self.workflow.acl.create(email="viewer@example.com", role=Role.VIEWER)
        self.workflow.acl.create(
            email="report_viewer@example.com", role=Role.REPORT_VIEWER
        )

    def tearDown(self):
        self.log_patcher.stop()
        self.queue_render_patcher.stop()
        super().tearDown()

    def _set_public_and_secret_id(self, public: bool, secret_id: str) -> None:
        self.workflow.public = public
        self.workflow.secret_id = secret_id
        self.workflow.save(update_fields=["public", "secret_id"])

    def _assert_responses(
        self,
        path: str,
        expected_owner_response: int,
        expected_viewer_response: int,
        expected_report_viewer_response: int,
        expected_other_user_response: int,
        expected_anonymous_response: int,
    ) -> None:
        test_name = "public=%r secret_id=%s path=%s" % (
            self.workflow.public,
            self.workflow.secret_id,
            path,
        )

        with self.subTest(test_name + " anonymous"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, expected_other_user_response)

        with self.subTest(test_name + " owner"):
            self.client.force_login(self.owner)
            response = self.client.get(path)
            self.assertEqual(response.status_code, expected_owner_response)

        with self.subTest(test_name + " viewer"):
            self.client.force_login(self.viewer)
            response = self.client.get(path)
            self.assertEqual(response.status_code, expected_viewer_response)

        with self.subTest(test_name + " report_viewer"):
            self.client.force_login(self.report_viewer)
            response = self.client.get(path)
            self.assertEqual(response.status_code, expected_report_viewer_response)

        with self.subTest(test_name + " other_user"):
            self.client.force_login(self.other_user)
            response = self.client.get(path)
            self.assertEqual(response.status_code, expected_other_user_response)

    def test_id_link_private_workflow(self):
        self._set_public_and_secret_id(False, "")
        self._assert_responses(
            f"/workflows/{self.workflow.id}/",
            expected_owner_response=200,
            expected_viewer_response=200,
            expected_report_viewer_response=403,
            expected_other_user_response=403,
            expected_anonymous_response=403,
        )

    def test_id_link_private_workflow_with_secret_id(self):
        self._set_public_and_secret_id(False, "anyoldsecret")
        self._assert_responses(
            f"/workflows/{self.workflow.id}/",
            expected_owner_response=200,
            expected_viewer_response=200,
            expected_report_viewer_response=403,
            expected_other_user_response=403,
            expected_anonymous_response=403,
        )

    def test_id_link_public_workflow(self):
        self._set_public_and_secret_id(True, "")
        self._assert_responses(
            f"/workflows/{self.workflow.id}/",
            expected_owner_response=200,
            expected_viewer_response=200,
            expected_report_viewer_response=200,
            expected_other_user_response=200,
            expected_anonymous_response=200,
        )

    def test_id_link_public_workflow_with_secret_id(self):
        self._set_public_and_secret_id(True, "anyoldsecret")
        self._assert_responses(
            f"/workflows/{self.workflow.id}/",
            expected_owner_response=200,
            expected_viewer_response=200,
            expected_report_viewer_response=200,
            expected_other_user_response=200,
            expected_anonymous_response=200,
        )

    def test_secret_link_private_workflow(self):
        self._set_public_and_secret_id(False, "wanyoldsecret")
        self._assert_responses(
            f"/workflows/wanyoldsecret/",
            expected_owner_response=302,
            expected_viewer_response=302,
            expected_report_viewer_response=200,
            expected_other_user_response=200,
            expected_anonymous_response=200,
        )

    def test_secret_report_link_private_workflow(self):
        self._set_public_and_secret_id(False, "wanyoldsecret")
        self._assert_responses(
            f"/workflows/wanyoldsecret/report",
            expected_owner_response=302,
            expected_viewer_response=302,
            expected_report_viewer_response=302,
            expected_other_user_response=200,
            expected_anonymous_response=200,
        )

    def test_secret_link_public_workflow(self):
        self._set_public_and_secret_id(True, "wanyoldsecret")
        self._assert_responses(
            f"/workflows/wanyoldsecret/",
            expected_owner_response=302,
            expected_viewer_response=302,
            expected_report_viewer_response=302,
            expected_other_user_response=302,
            expected_anonymous_response=302,
        )

    def test_empty_string_is_not_secret_link(self):
        self._set_public_and_secret_id(False, "")
        self._assert_responses(
            f"/workflows//",
            expected_owner_response=404,
            expected_viewer_response=404,
            expected_report_viewer_response=404,
            expected_other_user_response=404,
            expected_anonymous_response=404,
        )
