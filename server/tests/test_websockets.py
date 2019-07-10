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
from server.websockets import ws_client_send_delta_async, queue_render_if_listening
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

        async def inner():
            # loop is created by run_with_async_db()
            loop = asyncio.get_event_loop()
            try:
                return await f(self, communicate, *args, **kwargs)
            finally:
                # Clean up communicators
                for communicator in communicators:
                    await communicator.disconnect()
                # Disconnect from RabbitMQ
                layer = get_channel_layer()
                connection = layer._get_connection_for_loop(loop)
                await connection.close()

            self.run_with_async_db(inner())

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

        self.user = User.objects.create(username="usual", email="usual@example.org")
        self.workflow = Workflow.create_and_init(name="Workflow 1", owner=self.user)
        self.application = self.mock_auth_middleware(create_url_router())

        self.communicators = []

    def mock_auth_middleware(self, application):
        def inner(scope):
            scope["user"] = self.user
            scope["session"] = FakeSession("a-key")
            return application(scope)

        return inner

    @async_test
    async def test_deny_missing_id(self, communicate):
        comm = communicate(self.application, "/workflows/98913123/")
        connected, _ = await comm.connect()
        self.assertFalse(connected)

    @async_test
    async def test_deny_other_users_workflow(self, communicate):
        other_workflow = Workflow.create_and_init(
            name="Workflow 2",
            owner=User.objects.create(username="other", email="other@example.org"),
        )
        comm = communicate(self.application, f"/workflows/{other_workflow.id}/")
        connected, _ = await comm.connect()
        self.assertFalse(connected)

    @async_test
    async def test_allow_anonymous_workflow(self, communicate):
        workflow = Workflow.create_and_init(
            owner=None, anonymous_owner_session_key="a-key"
        )
        self.user = AnonymousUser()
        comm = communicate(self.application, f"/workflows/{workflow.id}/")
        connected, _ = await comm.connect()
        self.assertTrue(connected)
        await comm.receive_from()  # ignore initial workflow delta

    @async_test
    async def test_deny_other_users_anonymous_workflow(self, communicate):
        workflow = Workflow.create_and_init(
            anonymous_owner_session_key="some-other-key"
        )
        comm = communicate(self.application, f"/workflows/{workflow.id}/")
        connected, _ = await comm.connect()
        self.assertFalse(connected)

    @async_test
    async def test_initial_workflow_data(self, communicate):
        comm = communicate(self.application, f"/workflows/{self.workflow.id}/")
        connected, _ = await comm.connect()
        self.assertTrue(connected)
        response = await comm.receive_from()
        data = json.loads(response)
        self.assertEqual(data["type"], "apply-delta")
        self.assertEqual(data["data"]["updateWorkflow"]["name"], self.workflow.name)

    @async_test
    async def test_message(self, communicate):
        comm = communicate(self.application, f"/workflows/{self.workflow.id}/")
        connected, _ = await comm.connect()
        self.assertTrue(connected)
        await comm.receive_from()  # ignore initial workflow delta
        await ws_client_send_delta_async(self.workflow.id, {})
        response = await comm.receive_from()
        self.assertEqual(json.loads(response), {"type": "apply-delta", "data": {}})

    @async_test
    async def test_two_clients_get_messages_on_same_workflow(self, communicate):
        comm1 = communicate(self.application, f"/workflows/{self.workflow.id}/")
        comm2 = communicate(self.application, f"/workflows/{self.workflow.id}/")
        connected1, _ = await comm1.connect()
        self.assertTrue(connected1)
        await comm1.receive_from()  # ignore initial workflow delta
        connected2, _ = await comm2.connect()
        self.assertTrue(connected2)
        await comm2.receive_from()  # ignore initial workflow delta
        await ws_client_send_delta_async(self.workflow.id, {})
        response1 = await comm1.receive_from()
        self.assertEqual(json.loads(response1), {"type": "apply-delta", "data": {}})
        response2 = await comm2.receive_from()
        self.assertEqual(json.loads(response2), {"type": "apply-delta", "data": {}})

    @async_test
    async def test_after_disconnect_client_gets_no_message(self, communicate):
        comm = communicate(self.application, f"/workflows/{self.workflow.id}/")
        connected, _ = await comm.connect()
        self.assertTrue(connected)
        await comm.receive_from()  # ignore initial workflow delta
        self.assertTrue(await comm.receive_nothing())

    @patch("server.rabbitmq.queue_render")
    @async_test
    async def test_queue_render_if_listening(self, communicate, queue_render):
        future_args = asyncio.get_event_loop().create_future()

        async def do_queue(*args):
            future_args.set_result(args)

        queue_render.side_effect = do_queue

        comm = communicate(self.application, f"/workflows/{self.workflow.id}/")
        connected, _ = await comm.connect()
        self.assertTrue(connected)
        await comm.receive_from()  # ignore initial workflow delta
        await queue_render_if_listening(self.workflow.id, 123)
        args = await asyncio.wait_for(future_args, 0.005)
        self.assertEqual(args, (self.workflow.id, 123))

    @patch("server.rabbitmq.queue_render")
    @async_test
    async def test_queue_render_if_not_listening(self, communicate, queue_render):
        future_args = asyncio.get_event_loop().create_future()

        async def do_queue(*args):
            future_args.set_result(args)

        queue_render.side_effect = do_queue

        comm = communicate(self.application, f"/workflows/{self.workflow.id}/")
        connected, _ = await comm.connect()
        self.assertTrue(connected)
        await comm.receive_from()  # ignore initial workflow delta

        with self.assertRaises(asyncio.TimeoutError):
            await asyncio.wait_for(future_args, 0.005)
        queue_render.assert_not_called()

    @patch("server.handlers.handle")
    @async_test
    async def test_invoke_handler(self, communicate, handler):
        ret = asyncio.Future()
        ret.set_result(handlers.HandlerResponse(123, data={"bar": "baz"}))
        handler.return_value = ret

        comm = communicate(self.application, f"/workflows/{self.workflow.id}/")
        connected, _ = await comm.connect()
        await comm.receive_from()  # ignore initial workflow delta

        await comm.send_to(
            """
            {
                "requestId": 123,
                "path": "foo.bar",
                "arguments": { "foo": "bar" }
            }
        """
        )
        response = json.loads(await comm.receive_from())
        self.assertEqual(
            response, {"response": {"requestId": 123, "data": {"bar": "baz"}}}
        )

        handler.assert_called()
        request = handler.call_args[0][0]
        self.assertEqual(request.request_id, 123)
        self.assertEqual(request.path, "foo.bar")
        self.assertEqual(request.arguments, {"foo": "bar"})

    @async_test
    async def test_handler_workflow_deleted(self, communicate):
        comm = communicate(self.application, f"/workflows/{self.workflow.id}/")
        connected, _ = await comm.connect()
        await comm.receive_from()  # ignore initial workflow delta

        self.workflow.delete()

        await comm.send_to(
            """
            {
                "requestId": 123,
                "path": "foo.bar",
                "arguments": { "foo": "bar" }
            }
        """
        )
        response = json.loads(await comm.receive_from())
        self.assertEqual(
            response, {"response": {"requestId": 123, "error": "Workflow was deleted"}}
        )

    @async_test
    async def test_handler_request_invalid_but_req_id_ok(self, communicate):
        comm = communicate(self.application, f"/workflows/{self.workflow.id}/")
        connected, _ = await comm.connect()
        await comm.receive_from()  # ignore initial workflow delta

        await comm.send_to(
            """
            {
                "requestId": 123,
                "arguments": { "foo": "bar" }
            }
        """
        )
        response = json.loads(await comm.receive_from())
        self.assertEqual(
            response,
            {"response": {"requestId": 123, "error": "request.path must be a string"}},
        )

    @async_test
    async def test_handler_request_without_request_id(self, communicate):
        comm = communicate(self.application, f"/workflows/{self.workflow.id}/")
        connected, _ = await comm.connect()
        await comm.receive_from()  # ignore initial workflow delta

        await comm.send_to(
            """
            {
                "requestId": "ceci n'est pas un requestId",
                "arguments": { "foo": "bar" }
            }
        """
        )
        response = json.loads(await comm.receive_from())
        self.assertEqual(
            response,
            {
                "response": {
                    "requestId": None,
                    "error": "request.requestId must be an integer",
                }
            },
        )

    @patch("server.rabbitmq.queue_render")
    @async_test
    async def test_connect_queues_render_if_needed(self, communicate, queue_render):
        """
        Queue a render if connecting to a stale workflow.
        """
        future_args = asyncio.get_event_loop().create_future()

        async def do_queue(*args):
            future_args.set_result(args)

        queue_render.side_effect = do_queue

        # Make it so the workflow needs a render
        self.workflow.tabs.first().wf_modules.create(
            order=0,
            module_id_name="whatever",
            last_relevant_delta_id=self.workflow.last_delta_id,
            cached_render_result_delta_id=None,
        )

        comm = communicate(self.application, f"/workflows/{self.workflow.id}")
        connected, _ = await comm.connect()
        self.assertTrue(connected)
        await comm.receive_from()  # ignore initial workflow delta
        args = await asyncio.wait_for(future_args, 0.005)
        self.assertEqual(args, (self.workflow.id, self.workflow.last_delta_id))
