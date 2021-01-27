from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.models import Session
from django.utils import timezone

from cjwstate.models import Workflow
from cjwstate.tests.utils import DbTestCase
from cjworkbench.models.plan import Plan
from cjworkbench.models.subscription import Subscription
from cjworkbench.models.userprofile import UserProfile
from server.handlers.autofetch import list_autofetches_json, isoformat


IsoDate1 = "2019-06-18T19:35:57.123Z"
IsoDate2 = "2019-06-18T19:36:42.234Z"


class AutoupdateTest(DbTestCase):
    maxDiff = 100000

    def test_list_autofetches_empty(self):
        user = User.objects.create(username="a", email="a@example.org")
        UserProfile.objects.create(user=user, max_fetches_per_day=500)
        Workflow.create_and_init(owner=user)
        result = list_autofetches_json({"user": user, "session": None})
        self.assertEqual(
            result, {"maxFetchesPerDay": 500, "nFetchesPerDay": 0, "autofetches": []}
        )

    def test_list_autofetches_gets_user_max_fetches_per_day(self):
        user = User.objects.create(username="a", email="a@example.org")
        UserProfile.objects.create(user=user, max_fetches_per_day=6000)
        Workflow.create_and_init(owner=user)
        result = list_autofetches_json({"user": user, "session": None})
        self.assertEqual(
            result, {"maxFetchesPerDay": 6000, "nFetchesPerDay": 0, "autofetches": []}
        )

    def test_list_autofetches_gets_plan_max_fetches_per_day(self):
        user = User.objects.create(username="a", email="a@example.org")
        plan = Plan.objects.create(
            stripe_price_id="price_123",
            stripe_product_id="prod_123",
            stripe_active=True,
            max_fetches_per_day=2000,
            stripe_amount=100,
            stripe_currency="usd",
        )
        Subscription.objects.create(
            user=user,
            plan=plan,
            stripe_subscription_id="sub_123",
            stripe_status="active",
            created_at=timezone.now(),
            renewed_at=timezone.now(),
        )
        UserProfile.objects.create(user=user, max_fetches_per_day=100)

        Workflow.create_and_init(owner=user)
        result = list_autofetches_json({"user": user, "session": None})
        self.assertEqual(result["maxFetchesPerDay"], 2000)

    def test_list_autofetches_with_deleted_user_profile(self):
        # There's no good reason for UserProfile to be separate from User. But
        # it is. So here we are -- sometimes it doesn't exist.
        user = User.objects.create(username="a", email="a@example.org")
        Workflow.create_and_init(owner=user)
        UserProfile.objects.filter(user=user).delete()
        user.refresh_from_db()
        result = list_autofetches_json({"user": user, "session": None})
        self.assertEqual(
            result, {"maxFetchesPerDay": 50, "nFetchesPerDay": 0, "autofetches": []}
        )

    def test_list_autofetches_two_workflows(self):
        user = User.objects.create(username="a", email="a@example.org")
        UserProfile.objects.create(user=user, max_fetches_per_day=500)
        workflow = Workflow.create_and_init(
            owner=user, name="W1", last_viewed_at=IsoDate1
        )
        step1 = workflow.tabs.first().steps.create(
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
        step2 = workflow2.tabs.first().steps.create(
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
                        "step": {"id": step1.id, "fetchInterval": 600, "order": 0},
                    },
                    {
                        "workflow": {
                            "id": workflow2.id,
                            "name": "W2",
                            "createdAt": isoformat(workflow2.creation_date),
                            "lastViewedAt": IsoDate2,
                        },
                        "tab": {"slug": "tab-1", "name": "Tab 1"},
                        "step": {"id": step2.id, "fetchInterval": 1200, "order": 0},
                    },
                ],
            },
        )

    def test_list_autofetches_ignore_non_auto_update(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user, name="W1")
        workflow.tabs.first().steps.create(
            order=0,
            slug="step-1",
            module_id_name="loadurl",
            auto_update_data=False,
            update_interval=600,
        )
        result = list_autofetches_json({"user": user, "session": None})
        self.assertEqual(result["autofetches"], [])

    def test_list_autofetches_ignore_deleted_step(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user, name="W1")
        workflow.tabs.first().steps.create(
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
        tab.steps.create(
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
        workflow2.tabs.first().steps.create(
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
        workflow.tabs.first().steps.create(
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
        self.assertEqual(result["maxFetchesPerDay"], 50)

    def test_list_autofetches_ignore_other_session(self):
        user = AnonymousUser()
        session = Session(session_key="foo")
        Workflow.create_and_init(anonymous_owner_session_key="foo")
        workflow2 = Workflow.create_and_init(anonymous_owner_session_key="bar")
        workflow2.tabs.first().steps.create(
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
        workflow.tabs.first().steps.create(
            order=0,
            slug="step-1",
            module_id_name="loadurl",
            auto_update_data=True,
            next_update=timezone.now(),
            update_interval=1200,
        )
        workflow2 = Workflow.create_and_init(anonymous_owner_session_key="foo")
        workflow2.tabs.first().steps.create(
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
