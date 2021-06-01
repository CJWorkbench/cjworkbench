from typing import Any, Dict

from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.models import Session

from cjwstate.models import Workflow
from cjwstate.models.fields import Role
from cjwstate.tests.utils import DbTestCase, create_test_user
from server.handlers import HandlerError
from server.handlers.util import lock_workflow_for_role


def scope(
    *,
    workflow,
    user=AnonymousUser(),
    session=Session(),
    path="path",
    arguments={},
    secret_id=None,
) -> Dict[str, Any]:
    return dict(
        user=user,
        session=session,
        workflow=workflow,
        path=path,
        arguments=arguments,
        url_route={"kwargs": {"workflow_id_or_secret_id": secret_id or workflow.id}},
    )


def assert_lock(workflow: Workflow, role: str, **kwargs):
    with lock_workflow_for_role(workflow, scope(workflow=workflow, **kwargs), role):
        pass


# TODO consider changing most of these tests to tests of is_workflow_authorized()
class LockWorkflowForRoleTest(DbTestCase):
    # Auth is a bit weird: we already know the user has access to the workflow
    # because the WebSockets connection didn't close. But we'd like to update
    # the auth with each request, so if Alice grants Bob new rights Bob should
    # get them right away. Also, the WebSockets connection only implies read
    # access; it doesn't imply owner/editor access.

    def test_auth_read_owner(self):
        workflow = Workflow.objects.create(owner=create_test_user())
        assert_lock(workflow, "owner", user=workflow.owner)

    def test_auth_read_public(self):
        workflow = Workflow.objects.create(owner=create_test_user(), public=True)
        assert_lock(workflow, "read")

    def test_auth_read_secret(self):
        workflow = Workflow.objects.create(
            owner=create_test_user(), public=False, secret_id="wsecret"
        )
        assert_lock(workflow, "read", secret_id="wsecret")

    def test_auth_read_viewer(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.objects.create()
        workflow.acl.create(email="a@example.org", role=Role.VIEWER)
        assert_lock(workflow, "read", user=user)

    def test_auth_read_deny_report_viewer(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.objects.create()
        workflow.acl.create(email="a@example.org", role=Role.REPORT_VIEWER)
        with self.assertRaises(
            HandlerError, msg="AuthError: no read access to workflow"
        ):
            assert_lock(workflow, "read", user=user)

    def test_auth_read_anonymous_owner(self):
        session = Session(session_key="foo")
        workflow = Workflow.objects.create(
            anonymous_owner_session_key=session.session_key
        )
        assert_lock(workflow, "read", session=session)

    def test_auth_read_deny_non_owner(self):
        workflow = Workflow.objects.create(owner=create_test_user())
        with self.assertRaises(
            HandlerError, msg="AuthError: no read access to workflow"
        ):
            assert_lock(workflow, "read")

    def test_auth_write_owner(self):
        workflow = Workflow.objects.create(owner=create_test_user())
        assert_lock(workflow, "write", user=workflow.owner)

    def test_auth_write_deny_viewer(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.objects.create()
        workflow.acl.create(email="a@example.org", role=Role.VIEWER)
        with self.assertRaises(
            HandlerError, msg="AuthError: no write access to workflow"
        ):
            assert_lock(workflow, "write", user=user)

    def test_auth_write_deny_public(self):
        workflow = Workflow.objects.create(owner=create_test_user(), public=True)
        with self.assertRaises(
            HandlerError, msg="AuthError: no write access to workflow"
        ):
            assert_lock(workflow, "write")

    def test_auth_write_editor(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.objects.create()
        workflow.acl.create(email="a@example.org", role=Role.EDITOR)
        assert_lock(workflow, "write", user=user)

    def test_auth_write_anonymous_owner(self):
        session = Session(session_key="foo")
        workflow = Workflow.objects.create(
            anonymous_owner_session_key=session.session_key
        )
        assert_lock(workflow, "write", session=session)

    def test_auth_write_deny_non_owner(self):
        workflow = Workflow.objects.create(owner=create_test_user())
        with self.assertRaises(
            HandlerError, msg="AuthError: no write access to workflow"
        ):
            assert_lock(workflow, "write")

    def test_auth_owner_owner(self):
        workflow = Workflow.objects.create(owner=create_test_user())
        assert_lock(workflow, "owner", user=workflow.owner)

    def test_auth_owner_deny_public(self):
        workflow = Workflow.objects.create(owner=create_test_user(), public=True)
        with self.assertRaises(
            HandlerError, msg="AuthError: no owner access to workflow"
        ):
            assert_lock(workflow, "owner")

    def test_auth_owner_deny_editor(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.objects.create()
        workflow.acl.create(email="a@example.org", role=Role.EDITOR)
        with self.assertRaises(
            HandlerError, msg="AuthError: no owner access to workflow"
        ):
            assert_lock(workflow, "owner", user=user)

    def test_auth_owner_anonymous_owner(self):
        session = Session(session_key="foo")
        workflow = Workflow.objects.create(
            anonymous_owner_session_key=session.session_key
        )
        assert_lock(workflow, "owner", session=session)
