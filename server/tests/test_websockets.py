# Tests for our websockets (Channels) handling
# Pretty minimal rn, just tests that we can open a connection to a workflow

from channels import Channel
from channels.tests import ChannelTestCase, HttpClient
from server.models import Module, Workflow
from server.websockets import ws_send_workflow_update
from server.tests.utils import add_new_module, add_new_workflow

class ChannelTests(ChannelTestCase):
    def setUp(self):
        self.wf_id = add_new_workflow('Workflow 1')

    def test_connect(self):
        client = HttpClient()
        wf_path = '/workflow/' + str(self.wf_id)

        # cannot connect to an invalid workflow ID
        with self.assertRaises(AssertionError):
            client.send_and_consume('websocket.connect', path='/workflow/999999')
        self.assertIsNone(client.receive())

        # can connect to valid workflow ID
        client.send_and_consume('websocket.connect', path=wf_path)
        self.assertIsNone(client.receive())

        # send message
        ws_send_workflow_update(self.wf_id, {'foo':42})
        self.assertEqual(client.receive(), {'foo' : 42})

        # add another client to same workflow, test receive
        client2 = HttpClient()
        client2.send_and_consume('websocket.connect', path=wf_path)
        self.assertIsNone(client2.receive())

        ws_send_workflow_update(self.wf_id, {'bar': 42})
        self.assertEqual(client.receive(), {'bar': 42})
        self.assertEqual(client2.receive(), {'bar': 42})

        # remove client from workflow, test no longer receives
        client2.send_and_consume('websocket.disconnect', path=wf_path)
        self.assertIsNone(client2.receive())
        ws_send_workflow_update(self.wf_id, {'baz': 42})
        self.assertEqual(client.receive(), {'baz': 42})
        self.assertIsNone(client2.receive())



