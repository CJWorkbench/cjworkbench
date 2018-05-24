# Tests for our websockets (Channels) handling

import asyncio
from aiounittest import async_test
from channels.testing import WebsocketCommunicator
import json
from unittest import TestCase

from cjworkbench.asgi import create_url_router
from server.websockets import ws_client_rerender_workflow_async, ws_client_wf_module_status_async, WorkflowConsumer
from server.tests.utils import add_new_workflow, add_new_module_version, add_new_wf_module, LoggedInTestCase, create_test_user, clear_db

class ChannelTests(TestCase):
    def setUp(self):
        super(ChannelTests, self).setUp()

        clear_db()

        self.user = create_test_user(username='usual', email='usual@example.org')
        self.workflow = add_new_workflow('Workflow 1')
        self.wf_id = self.workflow.id
        self.module = add_new_module_version('Module')
        self.wf_module = add_new_wf_module(self.workflow, self.module)
        self.application = self.mock_auth_middleware(create_url_router())


    def tearDown(self):
        clear_db()


    def mock_auth_middleware(self, application):
        def inner(scope):
            scope['user'] = self.user
            return application(scope)
        return inner


    @async_test
    async def test_deny_missing_id(self):
        comm = WebsocketCommunicator(self.application, '/workflows/98913123/')
        connected, _ = await comm.connect()
        self.assertFalse(connected)


    @async_test
    async def test_deny_other_users_workflow(self):
        other_workflow = add_new_workflow(
                'Workflow 2',
                owner=create_test_user('other', 'other@example.org')
        )
        comm = WebsocketCommunicator(self.application, f'/workflows/{other_workflow.id}/')
        connected, _ = await comm.connect()
        self.assertFalse(connected)


    @async_test
    async def test_message(self):
        comm = WebsocketCommunicator(self.application, f'/workflows/{self.workflow.id}/')
        connected, _ = await comm.connect(); self.assertTrue(connected)
        await ws_client_rerender_workflow_async(self.workflow)
        response = await comm.receive_from()
        self.assertEqual(json.loads(response), { 'type': 'reload-workflow' })


    @async_test
    async def test_two_clients_get_messages_on_same_workflow(self):
        comm1 = WebsocketCommunicator(self.application, f'/workflows/{self.workflow.id}/')
        comm2 = WebsocketCommunicator(self.application, f'/workflows/{self.workflow.id}/')
        connected1, _ = await comm1.connect(); self.assertTrue(connected1)
        connected2, _ = await comm2.connect(); self.assertTrue(connected2)
        await ws_client_rerender_workflow_async(self.workflow)
        response1 = await comm1.receive_from()
        self.assertEqual(json.loads(response1), { 'type': 'reload-workflow' })
        response2 = await comm2.receive_from()
        self.assertEqual(json.loads(response2), { 'type': 'reload-workflow' })


    @async_test
    async def test_after_disconnect_client_gets_no_message(self):
        comm = WebsocketCommunicator(self.application, f'/workflows/{self.workflow.id}/')
        connected, _ = await comm.connect(); self.assertTrue(connected)
        await comm.disconnect()
        self.assertTrue(await comm.receive_nothing())


    @async_test
    async def test_wf_module_message(self):
        comm = WebsocketCommunicator(self.application, f'/workflows/{self.workflow.id}/')
        connected, _ = await comm.connect(); self.assertTrue(connected)
        await ws_client_wf_module_status_async(self.wf_module, 'busy')
        response = await comm.receive_from()
        self.assertEqual(json.loads(response), {
            'id': self.wf_module.id,
            'type': 'wfmodule-status',
            'status': 'busy',
        })
