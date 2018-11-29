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


class WebsocketsHandlerDecoratorTest(DbTestCase):
    def handle(self, *args, **kwargs):
        """handlers.handle(), synchronous."""
        return async_to_sync(handlers.handle)(*args, **kwargs)

    def call_handler(self, handler, *args, **kwargs):
        """Call handler, synchronously."""
        return async_to_sync(handler)(*args, **kwargs)

    def test_missing_handler(self):
        user = User()
        ret = self.handle(user, Session(), Workflow(owner=user),
                          'path.does.not.exist', {})
        self.assertEqual(ret, {'error': 'invalid path: path.does.not.exist'})

    def test_invalid_arguments(self):
        @handlers.websockets_handler(role='read')
        async def x(user, session, workflow, x):
            return None

        user = User()
        ret = self.call_handler(x, user, Session(), Workflow(owner=user),
                                {'y': 3})
        self.assertEqual(ret, {'error': (
            "invalid arguments: x() got an unexpected keyword argument 'y'"
        )})

    def test_return_something(self):
        @handlers.websockets_handler(role='read')
        async def x(user, session, workflow):
            return {'x': 'y'}

        user = User()
        ret = self.call_handler(x, user, Session(), Workflow(owner=user), {})
        self.assertEqual(ret, {'x': 'y'})

    def test_all_arguments_optional(self):
        @handlers.websockets_handler(role='read')
        async def x(**kwargs):
            return {'x': 'y'}

        user = User()
        ret = self.call_handler(x, user, Session(), Workflow(owner=user), {})
        self.assertEqual(ret, {'x': 'y'})

    def test_catch_any_error(self):
        @handlers.websockets_handler(role='read')
        async def x(**kwargs):
            raise ValueError('bad value')

        user = User()
        with self.assertLogs(level=logging.ERROR):
            ret = self.call_handler(x, user, Session(), Workflow(owner=user),
                                    {})
        self.assertEqual(ret, {'error': 'ValueError: bad value'})

    # Auth is a bit weird: we already know the user has access to the workflow
    # because the WebSockets connection didn't close. But we'd like to update
    # the auth with each request, so if Alice grants Bob new rights Bob should
    # get them right away.
    def test_auth_read_owner(self):
        user = User()
        ret = self.call_handler(handle_read, user, Session(),
                                Workflow(owner=user), {})
        self.assertEqual(ret, {'role': 'read'})

    def test_auth_read_public(self):
        ret = self.call_handler(handle_read, User(), Session(),
                                Workflow(owner=User(), public=True), {})
        self.assertEqual(ret, {'role': 'read'})

    def test_auth_read_viewer(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.objects.create()
        workflow.acl.create(email='a@example.org', can_edit=False)
        ret = self.call_handler(handle_read, user, Session(), workflow, {})
        self.assertEqual(ret, {'role': 'read'})

    def test_auth_read_anonymous_owner(self):
        user = AnonymousUser()
        session = Session(session_key='foo')
        workflow = Workflow(anonymous_owner_session_key=session.session_key)
        ret = self.call_handler(handle_read, user, session, workflow, {})
        self.assertEqual(ret, {'role': 'read'})

    def test_auth_read_deny_non_owner(self):
        ret = self.call_handler(handle_read, User(), Session(),
                                Workflow(owner=User()), {})
        self.assertEqual(ret, {
            'error': 'AuthError: no read access to workflow'
        })

    def test_auth_write_owner(self):
        user = User()
        ret = self.call_handler(handle_write, user, Session(),
                                Workflow(owner=user), {})
        self.assertEqual(ret, {'role': 'write'})

    def test_auth_write_deny_viewer(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.objects.create()
        workflow.acl.create(email='a@example.org', can_edit=False)
        ret = self.call_handler(handle_write, user, Session(), workflow, {})
        self.assertEqual(ret, {
            'error': 'AuthError: no write access to workflow'
        })

    def test_auth_write_deny_public(self):
        ret = self.call_handler(handle_write, User(), Session(),
                                Workflow(owner=User(), public=True), {})
        self.assertEqual(ret, {
            'error': 'AuthError: no write access to workflow'
        })

    def test_auth_write_editor(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.objects.create()
        workflow.acl.create(email='a@example.org', can_edit=True)
        ret = self.call_handler(handle_write, user, Session(), workflow, {})
        self.assertEqual(ret, {'role': 'write'})

    def test_auth_write_anonymous_owner(self):
        user = AnonymousUser()
        session = Session(session_key='foo')
        workflow = Workflow(anonymous_owner_session_key=session.session_key)
        ret = self.call_handler(handle_write, user, session, workflow, {})
        self.assertEqual(ret, {'role': 'write'})

    def test_auth_write_deny_non_owner(self):
        ret = self.call_handler(handle_write, User(), Session(),
                                Workflow(owner=User()), {})
        self.assertEqual(ret, {
            'error': 'AuthError: no write access to workflow'
        })

    def test_auth_owner_owner(self):
        user = User()
        ret = self.call_handler(handle_owner, user, Session(),
                                Workflow(owner=user), {})
        self.assertEqual(ret, {'role': 'owner'})

    def test_auth_owner_deny_public(self):
        ret = self.call_handler(handle_owner, User(), Session(),
                                Workflow(owner=User(), public=True), {})
        self.assertEqual(ret, {
            'error': 'AuthError: no owner access to workflow'
        })

    def test_auth_owner_deny_viewer(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.objects.create()
        workflow.acl.create(email='a@example.org', can_edit=False)
        ret = self.call_handler(handle_owner, user, Session(), workflow, {})
        self.assertEqual(ret, {
            'error': 'AuthError: no owner access to workflow'
        })

    def test_auth_owner_deny_editor(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.objects.create()
        workflow.acl.create(email='a@example.org', can_edit=True)
        ret = self.call_handler(handle_owner, user, Session(), workflow, {})
        self.assertEqual(ret, {
            'error': 'AuthError: no owner access to workflow'
        })

    def test_auth_owner_anonymous_owner(self):
        user = AnonymousUser()
        session = Session(session_key='foo')
        workflow = Workflow(anonymous_owner_session_key=session.session_key)
        ret = self.call_handler(handle_owner, user, session, workflow, {})
        self.assertEqual(ret, {'role': 'owner'})

    def test_auth_owner_deny_non_owner(self):
        ret = self.call_handler(handle_owner, User(), Session(),
                                Workflow(owner=User()), {})
        self.assertEqual(ret, {
            'error': 'AuthError: no owner access to workflow'
        })

    def test_register(self):
        @handlers.register_websockets_handler
        async def x(*args, **kwargs):
            return {'called': True}

        ret = self.handle(User(), Session(), Workflow(), x.__module__ + '.x', {})
        self.assertEqual(ret, {'called': True})
