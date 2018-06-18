import unittest
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.utils import timezone
from server.maintenance import delete_expired_anonymous_workflows
from server.models import Workflow
from server.tests.utils import clear_db

class TestDeleteExpiredAnonymousWorkflows(unittest.TestCase):
    def setUp(self):
        clear_db()

    def tearDown(self):
        clear_db()

    def _create_user(self, username: str) -> User:
        return User.objects.create(username=username,
                                   email=f'{username}@example.org',
                                   password='4Greac"dry')

    def _create_workflow(self, name: str, owner: User=None,
                         session_key: str=None) -> Workflow:
        return Workflow.objects.create(name=name, owner=owner,
                                       anonymous_owner_session_key=session_key)

    def _create_session(self, key: str) -> Session:
        return Session.objects.create(session_key=key,
                                      expire_date=timezone.now())

    def test_preserve_owner(self):
        owner = self._create_user('Alice')
        self._create_workflow('Workflow', owner=owner)

        delete_expired_anonymous_workflows()

        self.assertEqual(Workflow.objects.count(), 1)

    def test_preserve_anonymous_user(self):
        self._create_session('a-key')
        self._create_workflow('Workflow', session_key='a-key')

        delete_expired_anonymous_workflows()

        self.assertEqual(Workflow.objects.count(), 1)

    def test_delete_other_anonymous_user(self):
        self._create_session('a-key')
        self._create_workflow('Workflow', session_key='another-key')

        delete_expired_anonymous_workflows()

        self.assertEqual(Workflow.objects.count(), 0)
