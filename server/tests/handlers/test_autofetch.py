from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.models import Session
from django.utils import timezone
from server.handlers.autofetch import list_autofetches_json, isoformat
from cjwstate.models import Workflow
from cjwstate.tests.utils import DbTestCase


IsoDate1 = "2019-06-18T19:35:57.123Z"
IsoDate2 = "2019-06-18T19:36:42.234Z"


class AutoupdateTest(DbTestCase):
    maxDiff = 100000

    def test_list_autofetches_empty(self):
        user = User.objects.create(username="a", email="a@example.org")
        Workflow.create_and_init(owner=user)
        result = list_autofetches_json({"user": user, "session": None})
        self.assertEqual(
            result, {"maxFetchesPerDay": 500, "nFetchesPerDay": 0, "autofetches": []}
        )

    def test_list_autofetches_gets_user_max_fetches_per_day(self):
        user = User.objects.create(username="a", email="a@example.org")
        user.user_profile.max_fetches_per_day = 6000
        user.user_profile.save(update_fields=["max_fetches_per_day"])
        Workflow.create_and_init(owner=user)
        result = list_autofetches_json({"user": user, "session": None})
        self.assertEqual(
            result, {"maxFetchesPerDay": 6000, "nFetchesPerDay": 0, "autofetches": []}
        )

    def test_list_autofetches_with_deleted_user_profile(self):
        # There's no good reason for UserProfile to be separate from User. But
        # it is. So here we are -- sometimes it doesn't exist.
        user = User.objects.create(username="a", email="a@example.org")
        Workflow.create_and_init(owner=user)
        user.user_profile.delete()
        user.refresh_from_db()
        result = list_autofetches_json({"user": user, "session": None})
        self.assertEqual(
            result, {"maxFetchesPerDay": 500, "nFetchesPerDay": 0, "autofetches": []}
        )

    def test_list_autofetches_two_workflows(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(
            owner=user, name="W1", last_viewed_at=IsoDate1
        )
        step1 = workflow.tabs.first().wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="loadurl",
            auto_update_data=True,
            next_update=timezone.now(),
            update_interval=600,
        )
        workflow2 = Workflow.create_and_init(
            owner=user, name="W2", last_viewed_at=IsoDate2
        )
        step2 = workflow2.tabs.first().wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="loadurl",
            auto_update_data=True,
            next_update=timezone.now(),
            update_interval=1200,
        )

        result = list_autofetches_json({"user": user, "session": None})
        self.assertEqual(
            result,
            {
                "maxFetchesPerDay": 500,
                "nFetchesPerDay": 216,
                "autofetches": [
                    {
                        "workflow": {
                            "id": workflow.id,
                            "name": "W1",
                            "createdAt": isoformat(workflow.creation_date),
                            "lastViewedAt": IsoDate1,
                        },
                        "tab": {"slug": "tab-1", "name": "Tab 1"},
                        "wfModule": {"id": step1.id, "fetchInterval": 600, "order": 0},
                    },
                    {
                        "workflow": {
                            "id": workflow2.id,
                            "name": "W2",
                            "createdAt": isoformat(workflow2.creation_date),
                            "lastViewedAt": IsoDate2,
                        },
                        "tab": {"slug": "tab-1", "name": "Tab 1"},
                        "wfModule": {"id": step2.id, "fetchInterval": 1200, "order": 0},
                    },
                ],
            },
        )

    def test_list_autofetches_ignore_non_auto_update(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user, name="W1")
        workflow.tabs.first().wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="loadurl",
            auto_update_data=False,
            update_interval=600,
        )
        result = list_autofetches_json({"user": user, "session": None})
        self.assertEqual(result["autofetches"], [])

    def test_list_autofetches_ignore_deleted_wf_module(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user, name="W1")
        workflow.tabs.first().wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="loadurl",
            auto_update_data=True,
            next_update=timezone.now(),
            update_interval=600,
            is_deleted=True,
        )
        result = list_autofetches_json({"user": user, "session": None})
        self.assertEqual(result["autofetches"], [])

    def test_list_autofetches_ignore_deleted_tab(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user, name="W1")
        tab = workflow.tabs.create(position=1, slug="tab-deleted", is_deleted=True)
        tab.wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="loadurl",
            auto_update_data=True,
            next_update=timezone.now(),
            update_interval=600,
        )
        result = list_autofetches_json({"user": user, "session": None})
        self.assertEqual(result["autofetches"], [])

    def test_list_autofetches_ignore_wrong_user(self):
        user = User.objects.create(username="a", email="a@example.org")
        Workflow.create_and_init(owner=user)

        user2 = User.objects.create(username="b", email="b@example.org")
        workflow2 = Workflow.create_and_init(owner=user2)
        workflow2.tabs.first().wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="loadurl",
            auto_update_data=True,
            next_update=timezone.now(),
            update_interval=600,
        )

        result = list_autofetches_json({"user": user, "session": None})
        self.assertEqual(result["autofetches"], [])

    def test_list_autofetches_session(self):
        user = AnonymousUser()
        session = Session(session_key="foo")
        workflow = Workflow.create_and_init(anonymous_owner_session_key="foo")
        workflow.tabs.first().wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="loadurl",
            auto_update_data=True,
            next_update=timezone.now(),
            update_interval=600,
        )
        result = list_autofetches_json({"user": user, "session": session})
        self.assertEqual(result["autofetches"][0]["workflow"]["id"], workflow.id)

    def test_list_autofetches_session_gets_default_max_fetches_per_day(self):
        user = AnonymousUser()
        session = Session(session_key="foo")
        Workflow.create_and_init(anonymous_owner_session_key="foo")
        result = list_autofetches_json({"user": user, "session": session})
        self.assertEqual(result["maxFetchesPerDay"], 500)

    def test_list_autofetches_ignore_other_session(self):
        user = AnonymousUser()
        session = Session(session_key="foo")
        Workflow.create_and_init(anonymous_owner_session_key="foo")
        workflow2 = Workflow.create_and_init(anonymous_owner_session_key="bar")
        workflow2.tabs.first().wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="loadurl",
            auto_update_data=True,
            next_update=timezone.now(),
            update_interval=600,
        )
        result = list_autofetches_json({"user": user, "session": session})
        self.assertEqual(result["autofetches"], [])

    def test_list_autofetches_list_both_session_and_user(self):
        user = User.objects.create(username="a", email="a@example.org")
        session = Session(session_key="foo")
        workflow = Workflow.create_and_init(owner_id=user.id)
        workflow.tabs.first().wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="loadurl",
            auto_update_data=True,
            next_update=timezone.now(),
            update_interval=1200,
        )
        workflow2 = Workflow.create_and_init(anonymous_owner_session_key="foo")
        workflow2.tabs.first().wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="loadurl",
            auto_update_data=True,
            next_update=timezone.now(),
            update_interval=600,
        )
        result = list_autofetches_json({"user": user, "session": session})
        self.assertEqual(
            [a["workflow"]["id"] for a in result["autofetches"]],
            [workflow2.id, workflow.id],  # ordered by update_interval
        )
