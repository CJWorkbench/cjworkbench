import logging
import unittest
from asgiref.sync import async_to_sync
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.models import Session
from server import handlers
from server.models import Workflow
from ..utils import DbTestCase  # some ACL stuff needs database


@handlers.websockets_handler(role='read')
async def handle_read(workflow, **kwargs):
    return {'role': 'read'}


@handlers.websockets_handler(role='write')
async def handle_write(workflow, **kwargs):
    return {'role': 'write'}


@handlers.websockets_handler(role='owner')
async def handle_owner(workflow, **kwargs):
    return {'role': 'owner'}


DefaultKwargs = {
    'user': AnonymousUser(),
    'session': Session(),
    'workflow': Workflow(),
    'path': 'path',
    'arguments': {}
}


class WebsocketsHandlerDecoratorTest(DbTestCase):
    def handle(self, **kwargs):
        """handlers.handle(), synchronous."""
        for k, v in DefaultKwargs.items():
            kwargs.setdefault(k, v)
        request = handlers.HandlerRequest(1, **kwargs)
        return async_to_sync(handlers.handle)(request)

    def call_handler(self, handler, **kwargs):
        """Call handler, synchronously."""
        for k, v in DefaultKwargs.items():
            kwargs.setdefault(k, v)
        request = handlers.HandlerRequest(1, **kwargs)
        return async_to_sync(handler)(request)

    def assertHandlerResponse(self, response, data={}, error=''):
        self.assertEqual({'data': response.data, 'error': response.error},
                         {'data': data, 'error': error})

    def test_missing_handler(self):
        ret = self.handle(path='path.does.not.exist')
        self.assertHandlerResponse(ret,
                                   error='invalid path: path.does.not.exist')

    def test_invalid_arguments(self):
        @handlers.websockets_handler(role='read')
        async def x(user, session, workflow, x):
            return None

        user = User()
        ret = self.call_handler(x, user=user, workflow=Workflow(owner=user),
                                arguments={'y': 3})
        self.assertHandlerResponse(ret, error=(
            "invalid arguments: x() got an unexpected keyword argument 'y'"
        ))

    def test_return_something(self):
        @handlers.websockets_handler(role='read')
        async def x(user, session, workflow):
            return {'x': 'y'}

        user = User()
        ret = self.call_handler(x, user=user, workflow=Workflow(owner=user))
        self.assertHandlerResponse(ret, {'x': 'y'})

    def test_all_arguments_optional(self):
        @handlers.websockets_handler(role='read')
        async def x(**kwargs):
            return {'x': 'y'}

        user = User()
        ret = self.call_handler(x, user=user, workflow=Workflow(owner=user))
        self.assertHandlerResponse(ret, {'x': 'y'})

    def test_catch_any_error(self):
        @handlers.websockets_handler(role='read')
        async def x(**kwargs):
            raise ValueError('bad value')

        user = User()
        with self.assertLogs(level=logging.ERROR):
            ret = self.call_handler(x, user=user,
                                    workflow=Workflow(owner=user))
        self.assertHandlerResponse(ret, error='ValueError: bad value')

    # Auth is a bit weird: we already know the user has access to the workflow
    # because the WebSockets connection didn't close. But we'd like to update
    # the auth with each request, so if Alice grants Bob new rights Bob should
    # get them right away.
    def test_auth_read_owner(self):
        user = User()
        ret = self.call_handler(handle_read, user=user,
                                workflow=Workflow(owner=user))
        self.assertHandlerResponse(ret, {'role': 'read'})

    def test_auth_read_public(self):
        ret = self.call_handler(handle_read,
                                workflow=Workflow(owner=User(), public=True))
        self.assertHandlerResponse(ret, {'role': 'read'})

    def test_auth_read_viewer(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.objects.create()
        workflow.acl.create(email='a@example.org', can_edit=False)
        ret = self.call_handler(handle_read, user=user, workflow=workflow)
        self.assertHandlerResponse(ret, {'role': 'read'})

    def test_auth_read_anonymous_owner(self):
        user = AnonymousUser()
        session = Session(session_key='foo')
        workflow = Workflow(anonymous_owner_session_key=session.session_key)
        ret = self.call_handler(handle_read, user=user, session=session,
                                workflow=workflow)
        self.assertHandlerResponse(ret, {'role': 'read'})

    def test_auth_read_deny_non_owner(self):
        ret = self.call_handler(handle_read, workflow=Workflow(owner=User()))
        self.assertHandlerResponse(ret, error=(
            'AuthError: no read access to workflow'
        ))

    def test_auth_write_owner(self):
        user = User()
        ret = self.call_handler(handle_write, user=user,
                                workflow=Workflow(owner=user))
        self.assertHandlerResponse(ret, {'role': 'write'})

    def test_auth_write_deny_viewer(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.objects.create()
        workflow.acl.create(email='a@example.org', can_edit=False)
        ret = self.call_handler(handle_write, user=user, workflow=workflow)
        self.assertHandlerResponse(ret, error=(
            'AuthError: no write access to workflow'
        ))

    def test_auth_write_deny_public(self):
        ret = self.call_handler(handle_write,
                                workflow=Workflow(owner=User(), public=True))
        self.assertHandlerResponse(ret, error=(
            'AuthError: no write access to workflow'
        ))

    def test_auth_write_editor(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.objects.create()
        workflow.acl.create(email='a@example.org', can_edit=True)
        ret = self.call_handler(handle_write, user=user, workflow=workflow)
        self.assertHandlerResponse(ret, {'role': 'write'})

    def test_auth_write_anonymous_owner(self):
        user = AnonymousUser()
        session = Session(session_key='foo')
        workflow = Workflow(anonymous_owner_session_key=session.session_key)
        ret = self.call_handler(handle_write, user=user, session=session,
                                workflow=workflow)
        self.assertHandlerResponse(ret, {'role': 'write'})

    def test_auth_write_deny_non_owner(self):
        ret = self.call_handler(handle_write, workflow=Workflow(owner=User()))
        self.assertHandlerResponse(ret, error=(
            'AuthError: no write access to workflow'
        ))

    def test_auth_owner_owner(self):
        user = User()
        ret = self.call_handler(handle_owner, user=user,
                                workflow=Workflow(owner=user))
        self.assertHandlerResponse(ret, {'role': 'owner'})

    def test_auth_owner_deny_public(self):
        ret = self.call_handler(handle_owner,
                                workflow=Workflow(owner=User(), public=True))
        self.assertHandlerResponse(ret, error=(
            'AuthError: no owner access to workflow'
        ))

    def test_auth_owner_deny_viewer(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.objects.create()
        workflow.acl.create(email='a@example.org', can_edit=False)
        ret = self.call_handler(handle_owner, user=user, workflow=workflow)
        self.assertHandlerResponse(ret, error=(
            'AuthError: no owner access to workflow'
        ))

    def test_auth_owner_deny_editor(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.objects.create()
        workflow.acl.create(email='a@example.org', can_edit=True)
        ret = self.call_handler(handle_owner, user=user, workflow=workflow)
        self.assertHandlerResponse(ret, error=(
            'AuthError: no owner access to workflow'
        ))

    def test_auth_owner_anonymous_owner(self):
        user = AnonymousUser()
        session = Session(session_key='foo')
        workflow = Workflow(anonymous_owner_session_key=session.session_key)
        ret = self.call_handler(handle_owner, user=user, session=session,
                                workflow=workflow)
        self.assertHandlerResponse(ret, {'role': 'owner'})

    def test_auth_owner_deny_non_owner(self):
        ret = self.call_handler(handle_owner, workflow=Workflow(owner=User()))
        self.assertHandlerResponse(ret, error=(
            'AuthError: no owner access to workflow'
        ))

    def test_register(self):
        @handlers.register_websockets_handler
        async def x(*args, **kwargs):
            return handlers.HandlerResponse(1, {'called': True})

        ret = self.handle(path=x.__module__ + '.x')
        self.assertHandlerResponse(ret, {'called': True})
