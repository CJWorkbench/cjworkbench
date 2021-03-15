import asyncio
import logging

from asgiref.sync import async_to_sync
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.models import Session

from cjwstate.models import Workflow
from cjwstate.models.fields import Role
from server import handlers
from server.handlers import HandlerError, HandlerResponse, decorators

from .util import HandlerTestCase


@decorators.websockets_handler(role="read")
async def handle_read(workflow, **kwargs):
    return {"role": "read"}


@decorators.websockets_handler(role="write")
async def handle_write(workflow, **kwargs):
    return {"role": "write"}


@decorators.websockets_handler(role="owner")
async def handle_owner(workflow, **kwargs):
    return {"role": "owner"}


DefaultKwargs = {
    "user": AnonymousUser(),
    "session": Session(),
    "workflow": Workflow(),
    "path": "path",
    "arguments": {},
}


class WebsocketsHandlerDecoratorTest(HandlerTestCase):
    def handle(self, **kwargs):
        """handlers.handle(), synchronous."""
        request = self.build_request(**kwargs)
        return async_to_sync(handlers.handle)(request)

    def assertHandlerResponse(self, response, data=None, error=""):
        self.assertEqual(
            {"data": response.data, "error": response.error},
            {"data": data, "error": error},
        )

    def test_missing_handler(self):
        ret = self.handle(path="path.does.not.exist")
        self.assertHandlerResponse(ret, error="invalid path: path.does.not.exist")

    def test_invalid_arguments(self):
        @decorators.websockets_handler(role="read")
        async def x(scope, workflow, x):
            return None

        user = User()
        ret = self.run_handler(
            x, user=user, workflow=Workflow(owner=user), arguments={"y": 3}
        )
        self.assertHandlerResponse(
            ret, error=("invalid arguments: x() got an unexpected keyword argument 'y'")
        )

    def test_return_something(self):
        @decorators.websockets_handler(role="read")
        async def x(scope, workflow):
            return {"x": "y"}

        user = User()
        ret = self.run_handler(x, user=user, workflow=Workflow(owner=user))
        self.assertHandlerResponse(ret, {"x": "y"})

    def test_log_requests(self):
        @decorators.websockets_handler(role="read")
        async def x(scope, workflow):
            return {"x": "y"}

        user = User()
        workflow = Workflow(id=1, owner=user)
        request = self.build_request(path="a.path", user=user, workflow=workflow)
        with self.assertLogs(decorators.logger, level=logging.INFO) as cm:
            self.run_with_async_db(x(request))
            self.assertEqual(
                cm.output, ["INFO:server.handlers.decorators:a.path(workflow=1)"]
            )

    def test_all_arguments_optional(self):
        @decorators.websockets_handler(role="read")
        async def x(**kwargs):
            return {"x": "y"}

        user = User()
        ret = self.run_handler(x, user=user, workflow=Workflow(owner=user))
        self.assertHandlerResponse(ret, {"x": "y"})

    def test_catch_handlererror(self):
        @decorators.websockets_handler(role="read")
        async def x(**kwargs):
            raise HandlerError("should not be logged")

        user = User()
        ret = self.run_handler(x, user=user, workflow=Workflow(owner=user))
        self.assertHandlerResponse(ret, error="should not be logged")

    def test_catch_any_error(self):
        @decorators.websockets_handler(role="read")
        async def x(**kwargs):
            raise ValueError("bad value")

        user = User()
        with self.assertLogs(level=logging.ERROR):
            ret = self.run_handler(x, user=user, workflow=Workflow(owner=user))
        self.assertHandlerResponse(ret, error="ValueError: bad value")

    def test_passthrough_cancellederror(self):
        """
        CancelledError must be re-raised.

        Async functions may raise CancelledError at any time It must be
        re-raised. There's no way to avoid it. (asyncio.shield() in particular
        is not a way to avoid CancelledError: it's nothing but a waste of time;
        if you don't believe that go and look it up -- proving it.)
        """

        @decorators.websockets_handler(role="read")
        async def x(**kwargs):
            raise asyncio.CancelledError

        user = User()
        with self.assertRaises(asyncio.CancelledError):
            self.run_handler(x, user=user, workflow=Workflow(owner=user))

    # Auth is a bit weird: we already know the user has access to the workflow
    # because the WebSockets connection didn't close. But we'd like to update
    # the auth with each request, so if Alice grants Bob new rights Bob should
    # get them right away.
    def test_auth_read_owner(self):
        user = User()
        ret = self.run_handler(handle_read, user=user, workflow=Workflow(owner=user))
        self.assertHandlerResponse(ret, {"role": "read"})

    def test_auth_read_public(self):
        ret = self.run_handler(
            handle_read, workflow=Workflow(owner=User(), public=True)
        )
        self.assertHandlerResponse(ret, {"role": "read"})

    def test_auth_read_viewer(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.objects.create()
        workflow.acl.create(email="a@example.org", role=Role.VIEWER)
        ret = self.run_handler(handle_read, user=user, workflow=workflow)
        self.assertHandlerResponse(ret, {"role": "read"})

    def test_auth_read_deny_report_viewer(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.objects.create()
        workflow.acl.create(email="a@example.org", role=Role.REPORT_VIEWER)
        ret = self.run_handler(handle_read, user=user, workflow=workflow)
        self.assertHandlerResponse(ret, error=("AuthError: no read access to workflow"))

    def test_auth_read_anonymous_owner(self):
        user = AnonymousUser()
        session = Session(session_key="foo")
        workflow = Workflow(anonymous_owner_session_key=session.session_key)
        ret = self.run_handler(
            handle_read, user=user, session=session, workflow=workflow
        )
        self.assertHandlerResponse(ret, {"role": "read"})

    def test_auth_read_deny_non_owner(self):
        ret = self.run_handler(handle_read, workflow=Workflow(owner=User()))
        self.assertHandlerResponse(ret, error=("AuthError: no read access to workflow"))

    def test_auth_write_owner(self):
        user = User()
        ret = self.run_handler(handle_write, user=user, workflow=Workflow(owner=user))
        self.assertHandlerResponse(ret, {"role": "write"})

    def test_auth_write_deny_viewer(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.objects.create()
        workflow.acl.create(email="a@example.org", role=Role.VIEWER)
        ret = self.run_handler(handle_write, user=user, workflow=workflow)
        self.assertHandlerResponse(
            ret, error=("AuthError: no write access to workflow")
        )

    def test_auth_write_deny_public(self):
        ret = self.run_handler(
            handle_write, workflow=Workflow(owner=User(), public=True)
        )
        self.assertHandlerResponse(
            ret, error=("AuthError: no write access to workflow")
        )

    def test_auth_write_editor(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.objects.create()
        workflow.acl.create(email="a@example.org", role=Role.EDITOR)
        ret = self.run_handler(handle_write, user=user, workflow=workflow)
        self.assertHandlerResponse(ret, {"role": "write"})

    def test_auth_write_anonymous_owner(self):
        user = AnonymousUser()
        session = Session(session_key="foo")
        workflow = Workflow(anonymous_owner_session_key=session.session_key)
        ret = self.run_handler(
            handle_write, user=user, session=session, workflow=workflow
        )
        self.assertHandlerResponse(ret, {"role": "write"})

    def test_auth_write_deny_non_owner(self):
        ret = self.run_handler(handle_write, workflow=Workflow(owner=User()))
        self.assertHandlerResponse(
            ret, error=("AuthError: no write access to workflow")
        )

    def test_auth_owner_owner(self):
        user = User()
        ret = self.run_handler(handle_owner, user=user, workflow=Workflow(owner=user))
        self.assertHandlerResponse(ret, {"role": "owner"})

    def test_auth_owner_deny_public(self):
        ret = self.run_handler(
            handle_owner, workflow=Workflow(owner=User(), public=True)
        )
        self.assertHandlerResponse(
            ret, error=("AuthError: no owner access to workflow")
        )

    def test_auth_owner_deny_viewer(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.objects.create()
        workflow.acl.create(email="a@example.org", role=Role.VIEWER)
        ret = self.run_handler(handle_owner, user=user, workflow=workflow)
        self.assertHandlerResponse(
            ret, error=("AuthError: no owner access to workflow")
        )

    def test_auth_owner_deny_editor(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.objects.create()
        workflow.acl.create(email="a@example.org", role=Role.EDITOR)
        ret = self.run_handler(handle_owner, user=user, workflow=workflow)
        self.assertHandlerResponse(
            ret, error=("AuthError: no owner access to workflow")
        )

    def test_auth_owner_anonymous_owner(self):
        user = AnonymousUser()
        session = Session(session_key="foo")
        workflow = Workflow(anonymous_owner_session_key=session.session_key)
        ret = self.run_handler(
            handle_owner, user=user, session=session, workflow=workflow
        )
        self.assertHandlerResponse(ret, {"role": "owner"})

    def test_auth_owner_deny_non_owner(self):
        ret = self.run_handler(handle_owner, workflow=Workflow(owner=User()))
        self.assertHandlerResponse(
            ret, error=("AuthError: no owner access to workflow")
        )

    def test_register(self):
        @decorators.register_websockets_handler
        async def x(*args, **kwargs):
            return HandlerResponse(1, {"called": True})

        ret = self.handle(path=x.__module__ + ".x")
        self.assertHandlerResponse(ret, {"called": True})
