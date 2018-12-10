import asyncio
from concurrent.futures import ThreadPoolExecutor
import functools
import json
import logging
from unittest.mock import patch
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import AnonymousUser, User
import django.db
from cjworkbench.asgi import create_url_router
from server import handlers
from server.models import Workflow
from server.websockets import ws_client_rerender_workflow_async, \
        queue_render_if_listening
from server.tests.utils import DbTestCase


def async_test(f):
    """
    Decorate a test to run in its own event loop.

    Usage:

        class MyTest(unittest.TestCase):
            def setUp():
                self.application = create_asgi_application()
                pass  # sync code only

            def tearDown():
                pass  # sync code only

            @async_test
            async def test_message(self, communicate):
                comm = communicate(self.application, '/path')
                connected, _ = await comm.connect()
                self.assertTrue(connected)

    Features:

        * Runs each test with its own event loop.
        * Disconnects all communicators, regardless of whether test passes.
    """
    @functools.wraps(f)
    def wrapper(self, *args, **kwargs):
        communicators = []

        def communicate(*args, **kwargs):
            ret = WebsocketCommunicator(*args, **kwargs)
            communicators.append(ret)
            return ret

        # Reset the thread-local event loop
        old_loop = asyncio.get_event_loop()
        if not old_loop.is_closed():
            old_loop.close()
        # Set a 1-thread ThreadPoolExecutor. That thread will open a DB
        # connection, and we'll be able to close it in disconnect_all().
        loop = asyncio.new_event_loop()
        loop.set_default_executor(ThreadPoolExecutor(1))
        asyncio.set_event_loop(loop)

        async def disconnect_all():
            for communicator in communicators:
                await communicator.disconnect()

            def disconnect_db():
                # Runs in the same thread that actually connected to the DB
                django.db.connections.close_all()
            await loop.run_in_executor(None, disconnect_db)

        async def inner():
            try:
                return await f(self, communicate, *args, **kwargs)
            finally:
                await disconnect_all()
                layer = get_channel_layer()
                connection = layer._get_connection_for_loop(loop)
                await connection.close()  # clean up on the RabbitMQ side

        with self.assertLogs():
            try:
                # Run the async function by running the loop to completion
                return loop.run_until_complete(inner())
            finally:
                # log something, so self.assertLogs() doesn't fail
                logger = logging.getLogger('this-test')
                logger.info('Warnings from closing event loop:')

                # Now call loop.close(). It will emit tons of log messages
                # about dead tasks but we don't care.
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()

            # Reset the thread-local event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

    return wrapper


class FakeSession:
    def __init__(self, session_key):
        self.session_key = session_key

    # channels.auth expects Session to behave like a dict
    def __getitem__(self, key):
        return None


class ChannelTests(DbTestCase):
    def setUp(self):
        super().setUp()

        self.user = User.objects.create(username='usual',
                                        email='usual@example.org')
        self.workflow = Workflow.objects.create(name='Workflow 1',
                                                owner=self.user)
        self.application = self.mock_auth_middleware(create_url_router())

        self.communicators = []

    def mock_auth_middleware(self, application):
        def inner(scope):
            scope['user'] = self.user
            scope['session'] = FakeSession('a-key')
            return application(scope)
        return inner

    @async_test
    async def test_deny_missing_id(self, communicate):
        comm = communicate(self.application, '/workflows/98913123/')
        connected, _ = await comm.connect()
        self.assertFalse(connected)

    @async_test
    async def test_deny_other_users_workflow(self, communicate):
        other_workflow = Workflow.objects.create(
                name='Workflow 2',
                owner=User.objects.create(username='other',
                                          email='other@example.org')
        )
        comm = communicate(self.application,
                           f'/workflows/{other_workflow.id}/')
        connected, _ = await comm.connect()
        self.assertFalse(connected)

    @async_test
    async def test_allow_anonymous_workflow(self, communicate):
        workflow = Workflow.objects.create(
            owner=None,
            anonymous_owner_session_key='a-key'
        )
        self.user = AnonymousUser()
        comm = communicate(self.application, f'/workflows/{workflow.id}/')
        connected, _ = await comm.connect()
        self.assertTrue(connected)

    @async_test
    async def test_deny_other_users_anonymous_workflow(self, communicate):
        workflow = Workflow.objects.create(
            anonymous_owner_session_key='some-other-key'
        )
        comm = communicate(self.application, f'/workflows/{workflow.id}/')
        connected, _ = await comm.connect()
        self.assertFalse(connected)

    @async_test
    async def test_message(self, communicate):
        comm = communicate(self.application, f'/workflows/{self.workflow.id}/')
        connected, _ = await comm.connect()
        self.assertTrue(connected)
        await ws_client_rerender_workflow_async(self.workflow)
        response = await comm.receive_from()
        self.assertEqual(json.loads(response), {'type': 'reload-workflow'})

    @async_test
    async def test_two_clients_get_messages_on_same_workflow(self,
                                                             communicate):
        comm1 = communicate(self.application,
                            f'/workflows/{self.workflow.id}/')
        comm2 = communicate(self.application,
                            f'/workflows/{self.workflow.id}/')
        connected1, _ = await comm1.connect()
        self.assertTrue(connected1)
        connected2, _ = await comm2.connect()
        self.assertTrue(connected2)
        await ws_client_rerender_workflow_async(self.workflow)
        response1 = await comm1.receive_from()
        self.assertEqual(json.loads(response1), {'type': 'reload-workflow'})
        response2 = await comm2.receive_from()
        self.assertEqual(json.loads(response2), {'type': 'reload-workflow'})

    @async_test
    async def test_after_disconnect_client_gets_no_message(self, communicate):
        comm = communicate(self.application, f'/workflows/{self.workflow.id}/')
        connected, _ = await comm.connect()
        self.assertTrue(connected)
        self.assertTrue(await comm.receive_nothing())

    @patch('server.rabbitmq.queue_render')
    @async_test
    async def test_queue_render_if_listening(self, communicate, queue_render):
        future_args = asyncio.get_event_loop().create_future()

        async def do_queue(*args):
            future_args.set_result(args)
        queue_render.side_effect = do_queue

        comm = communicate(self.application, f'/workflows/{self.workflow.id}/')
        connected, _ = await comm.connect()
        self.assertTrue(connected)
        await queue_render_if_listening(self.workflow.id, 123)
        args = await asyncio.wait_for(future_args, 0.005)
        self.assertEqual(args, (self.workflow.id, 123))

    @patch('server.rabbitmq.queue_render')
    @async_test
    async def test_queue_render_if_not_listening(self, communicate,
                                                 queue_render):
        future_args = asyncio.get_event_loop().create_future()

        async def do_queue(*args):
            future_args.set_result(args)
        queue_render.side_effect = do_queue

        comm = communicate(self.application, f'/workflows/{self.workflow.id}/')
        connected, _ = await comm.connect()
        self.assertTrue(connected)

        with self.assertRaises(asyncio.TimeoutError):
            await asyncio.wait_for(future_args, 0.005)
        queue_render.assert_not_called()

    @patch('server.handlers.handle')
    @async_test
    async def test_invoke_handler(self, communicate, handler):
        ret = asyncio.Future()
        ret.set_result(handlers.HandlerResponse(123, data={'bar': 'baz'}))
        handler.return_value = ret

        comm = communicate(self.application, f'/workflows/{self.workflow.id}/')
        connected, _ = await comm.connect()

        await comm.send_to('''
            {
                "requestId": 123,
                "path": "foo.bar",
                "arguments": { "foo": "bar" }
            }
        ''')
        response = json.loads(await comm.receive_from())
        self.assertEqual(response, {
            'response': {
                'requestId': 123,
                'data': {'bar': 'baz'},
            }
        })

        handler.assert_called()
        request = handler.call_args[0][0]
        self.assertEqual(request.request_id, 123)
        self.assertEqual(request.path, 'foo.bar')
        self.assertEqual(request.arguments, {'foo': 'bar'})

    @async_test
    async def test_handler_workflow_deleted(self, communicate):
        comm = communicate(self.application, f'/workflows/{self.workflow.id}/')
        connected, _ = await comm.connect()

        self.workflow.delete()

        await comm.send_to('''
            {
                "requestId": 123,
                "path": "foo.bar",
                "arguments": { "foo": "bar" }
            }
        ''')
        response = json.loads(await comm.receive_from())
        self.assertEqual(response, {
            'response': {
                'requestId': 123,
                'error': 'Workflow was deleted'
            }
        })

    @async_test
    async def test_handler_request_invalid_but_request_id_ok(self, communicate):
        comm = communicate(self.application, f'/workflows/{self.workflow.id}/')
        connected, _ = await comm.connect()

        await comm.send_to('''
            {
                "requestId": 123,
                "arguments": { "foo": "bar" }
            }
        ''')
        response = json.loads(await comm.receive_from())
        self.assertEqual(response, {
            'response': {
                'requestId': 123,
                'error': 'request.path must be a string',
            }
        })

    @async_test
    async def test_handler_request_without_request_id(self, communicate):
        comm = communicate(self.application, f'/workflows/{self.workflow.id}/')
        connected, _ = await comm.connect()

        await comm.send_to('''
            {
                "requestId": "ceci n'est pas un requestId",
                "arguments": { "foo": "bar" }
            }
        ''')
        response = json.loads(await comm.receive_from())
        self.assertEqual(response, {
            'response': {
                'requestId': None,
                'error': 'request.requestId must be an integer',
            }
        })
