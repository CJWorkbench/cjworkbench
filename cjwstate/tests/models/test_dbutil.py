from django.contrib.auth.models import User
from django.db import transaction

from cjworkbench.models.userprofile import UserProfile
from cjworkbench.models.userusage import UserUsage
from cjwstate.models.dbutil import query_user_usage
from cjwstate.models.workflow import Workflow
from cjwstate.tests.utils import DbTestCase


def create_user():
    user = User.objects.create(email="a@foo.com")
    UserProfile.objects.create(user=user)
    return user


class QueryUserUsageTest(DbTestCase):
    def test_no_workflows(self):
        user = create_user()
        usage = query_user_usage(user.id)
        self.assertEqual(usage, UserUsage(fetches_per_day=0))

    def test_no_fetches(self):
        user = create_user()
        Workflow.create_and_init(fetches_per_day=0)
        usage = query_user_usage(user.id)
        self.assertEqual(usage, UserUsage(fetches_per_day=0))

    def test_sum_fetches(self):
        user = create_user()
        Workflow.create_and_init(owner=user, fetches_per_day=1)
        Workflow.create_and_init(owner=user, fetches_per_day=0)
        Workflow.create_and_init(owner=user, fetches_per_day=2.12)
        usage = query_user_usage(user.id)
        self.assertEqual(usage, UserUsage(fetches_per_day=3.12))
