from datetime import timedelta
import logging
import unittest
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.utils import timezone
from cjwstate.models import Workflow
from cjwstate.tests.utils import clear_db
from cron import sessions


class TestDeleteExpiredAnonymousWorkflows(unittest.TestCase):
    def setUp(self):
        clear_db()

    def tearDown(self):
        clear_db()

    def _create_user(self, username: str) -> User:
        return User.objects.create(
            username=username, email=f"{username}@example.org", password='4Greac"dry'
        )

    def _create_workflow(
        self, name: str, owner: User = None, session_key: str = None
    ) -> Workflow:
        return Workflow.objects.create(
            name=name, owner=owner, anonymous_owner_session_key=session_key
        )

    def _create_session(self, key: str, expire_date=None) -> Session:
        if expire_date is None:
            # Expire one second in the future by default
            expire_date = timezone.now() + timedelta(0, 1)
        return Session.objects.create(session_key=key, expire_date=expire_date)

    def test_preserve_owner(self):
        owner = self._create_user("Alice")
        self._create_workflow("Workflow", owner=owner)

        sessions.delete_expired_sessions_and_workflows_sync()

        self.assertEqual(Workflow.objects.count(), 1)

    def test_preserve_anonymous_user(self):
        self._create_session("a-key")
        self._create_workflow("Workflow", session_key="a-key")

        sessions.delete_expired_sessions_and_workflows_sync()

        self.assertEqual(Workflow.objects.count(), 1)

    def test_delete_expired_anonymous_user(self):
        self._create_session("a-key", timezone.now() - timedelta(0, 1))
        self._create_workflow("Workflow", session_key="a-key")

        with self.assertLogs(sessions.__name__, logging.INFO):
            sessions.delete_expired_sessions_and_workflows_sync()

        self.assertEqual(Workflow.objects.count(), 0)
