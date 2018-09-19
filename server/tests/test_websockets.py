import asyncio
import functools
import json
from channels.testing import WebsocketCommunicator
from cjworkbench.asgi import create_url_router
from django.contrib.auth.models import AnonymousUser
from server.models import Workflow
from server.websockets import ws_client_rerender_workflow_async, \
        ws_client_wf_module_status_async
from server.tests.utils import DbTestCase, clear_db, add_new_workflow, \
        add_new_module_version, add_new_wf_module, create_test_user


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

        async def disconnect_all():
            for communicator in communicators:
                await communicator.disconnect()

        async def inner():
            try:
                return await f(self, communicate, *args, **kwargs)
            finally:
                await disconnect_all()

        # Reset the thread-local event loop
        old_loop = asyncio.get_event_loop()
        if not old_loop.is_closed():
            old_loop.close()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Run the async function by running the loop to completion
            return loop.run_until_complete(inner())
        finally:
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
        clear_db()

        self.user = create_test_user(username='usual',
                                     email='usual@example.org')
        self.workflow = add_new_workflow('Workflow 1')
        self.wf_id = self.workflow.id
        self.module = add_new_module_version('Module')
        self.wf_module = add_new_wf_module(self.workflow, self.module)
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
        other_workflow = add_new_workflow(
                'Workflow 2',
                owner=create_test_user('other', 'other@example.org')
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

    @async_test
    async def test_wf_module_message(self, communicate):
        comm = communicate(self.application, f'/workflows/{self.workflow.id}/')
        connected, _ = await comm.connect()
        self.assertTrue(connected)
        await ws_client_wf_module_status_async(self.wf_module, 'busy')
        response = await comm.receive_from()
        self.assertEqual(json.loads(response), {
            'id': self.wf_module.id,
            'type': 'wfmodule-status',
            'status': 'busy',
        })
