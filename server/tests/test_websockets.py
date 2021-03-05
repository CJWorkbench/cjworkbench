import asyncio
import contextlib
import functools
import json
import logging
from unittest.mock import patch

from channels.layers import channel_layers, get_channel_layer
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import AnonymousUser, User

import cjwstate.rabbitmq.connection
from cjworkbench.asgi import _url_router
from cjworkbench.sync import database_sync_to_async
from cjwstate import clientside, rabbitmq
from cjwstate.models import Workflow
from cjwstate.rabbitmq import (
    queue_render_if_consumers_are_listening,
    send_update_to_workflow_clients,
)
from cjwstate.tests.utils import DbTestCase
from server import handlers


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

        def communicate(url, path):
            ret = WebsocketCommunicator(url, path)
            communicators.append(ret)
            return ret

        async def inner():
            try:
                return await f(self, communicate, *args, **kwargs)
            finally:
                # Clean up communicators
                for communicator in communicators:
                    await communicator.disconnect()
                # Disconnect from RabbitMQ
                layer = get_channel_layer()
                try:
                    await layer.close()
                finally:
                    channel_layers.backends = {}

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
        self.application = self.mock_i18n_middleware(
            self.mock_auth_middleware(_url_router)
        )

        self.communicators = []

        self._log_overrides = []
        for logger_name, level in [
            ("server.websockets", logging.WARN),
            ("carehare", logging.WARN),
            ("channels_rabbitmq", logging.WARN),
        ]:
            logger = logging.getLogger(logger_name)
            self._log_overrides.append((logger_name, logger.level))
            logger.setLevel(level)

    def tearDown(self):
        for (logger_name, level) in self._log_overrides:
            logger = logging.getLogger(logger_name)
            logger.setLevel(level)
        super().tearDown()

    def mock_auth_middleware(self, application):
        async def inner(scope, receive, send):
            scope["user"] = self.user
            scope["session"] = FakeSession("a-key")
            return await application(scope, receive, send)

        return inner

    def mock_i18n_middleware(self, application, locale_id="en"):
        async def inner(scope, receive, send):
            scope["locale_id"] = locale_id
            return await application(scope, receive, send)

        return inner

    @contextlib.asynccontextmanager
    async def global_rabbitmq_connection(self):
        future_connection = get_channel_layer().carehare_connection
        try:
            cjwstate.rabbitmq.connection._global_awaitable_connection = (
                future_connection
            )
            connection = await future_connection
            await connection.queue_declare(rabbitmq.Render, durable=True)
            yield
        finally:
            cjwstate.rabbitmq.connection._global_awaitable_connection = None

    @async_test
    async def test_deny_missing_id(self, communicate):
        comm = communicate(self.application, "/workflows/98913123/")
        connected, _ = await comm.connect()
        self.assertFalse(connected)

    @async_test
    async def test_deny_other_users_workflow(self, communicate):
        @database_sync_to_async
        def init_db():
            return Workflow.create_and_init(
                name="Workflow 2",
                owner=User.objects.create(username="other", email="other@example.org"),
            )

        other_workflow = await init_db()
        comm = communicate(self.application, f"/workflows/{other_workflow.id}/")
        connected, _ = await comm.connect()
        self.assertFalse(connected)

    @async_test
    async def test_allow_anonymous_workflow(self, communicate):
        @database_sync_to_async
        def init_db():
            return Workflow.create_and_init(
                owner=None, anonymous_owner_session_key="a-key"
            )

        workflow = await init_db()
        self.user = AnonymousUser()
        comm = communicate(self.application, f"/workflows/{workflow.id}/")
        connected, _ = await comm.connect()
        self.assertTrue(connected)
        await comm.receive_from()  # ignore initial workflow delta

    @async_test
    async def test_deny_other_users_anonymous_workflow(self, communicate):
        @database_sync_to_async
        def init_db():
            return Workflow.create_and_init(
                anonymous_owner_session_key="some-other-key"
            )

        workflow = await init_db()
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
        async with self.global_rabbitmq_connection():
            await send_update_to_workflow_clients(self.workflow.id, clientside.Update())
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
        async with self.global_rabbitmq_connection():
            await send_update_to_workflow_clients(self.workflow.id, clientside.Update())
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

    @patch.object(rabbitmq, "queue_render")
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
        async with self.global_rabbitmq_connection():
            await queue_render_if_consumers_are_listening(self.workflow.id, 123)
        args = await asyncio.wait_for(future_args, 0.005)
        self.assertEqual(args, (self.workflow.id, 123))

    @patch.object(rabbitmq, "queue_render")
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

    @patch.object(handlers, "handle")
    @async_test
    async def test_invoke_handler(self, communicate, handler):
        async def mock_handler(*args, **kwargs):
            return handlers.HandlerResponse(123, data={"bar": "baz"})

        handler.side_effect = mock_handler

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

        @database_sync_to_async
        def break_db():
            self.workflow.delete()

        await break_db()

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

    @patch.object(rabbitmq, "queue_render")
    @async_test
    async def test_connect_queues_render_if_needed(self, communicate, queue_render):
        future_args = asyncio.get_event_loop().create_future()

        async def do_queue(*args):
            future_args.set_result(args)

        queue_render.side_effect = do_queue

        @database_sync_to_async
        def require_render():
            # Make it so the workflow needs a render
            self.workflow.tabs.first().steps.create(
                order=0,
                slug="step-1",
                module_id_name="whatever",
                last_relevant_delta_id=self.workflow.last_delta_id,
                cached_render_result_delta_id=None,
            )

        await require_render()

        comm = communicate(self.application, f"/workflows/{self.workflow.id}")
        connected, _ = await comm.connect()
        self.assertTrue(connected)
        await comm.receive_from()  # ignore initial workflow delta
        args = await asyncio.wait_for(future_args, 0.005)
        self.assertEqual(args, (self.workflow.id, self.workflow.last_delta_id))
