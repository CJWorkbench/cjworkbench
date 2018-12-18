from unittest.mock import patch
from server.models import Workflow
from server.models.commands import SetTabNameCommand
from server.tests.utils import DbTestCase


async def async_noop(*args, **kwargs):
    return


class SetTabNameCommandTest(DbTestCase):
    @patch('server.websockets.ws_client_send_delta_async', async_noop)
    def test_set_name(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        tab.name = 'foo'
        tab.save(update_fields=['name'])

        cmd = self.run_with_async_db(SetTabNameCommand.create(
            workflow=workflow,
            tab=tab,
            new_name='bar'
        ))
        tab.refresh_from_db()
        self.assertEqual(tab.name, 'bar')

        self.run_with_async_db(cmd.backward())
        tab.refresh_from_db()
        self.assertEqual(tab.name, 'foo')

        self.run_with_async_db(cmd.forward())
        tab.refresh_from_db()
        self.assertEqual(tab.name, 'bar')

    @patch('server.websockets.ws_client_send_delta_async')
    def test_ws_data(self, send_delta):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        tab.name = 'foo'
        tab.save(update_fields=['name'])

        send_delta.return_value = async_noop()
        cmd = self.run_with_async_db(SetTabNameCommand.create(
            workflow=workflow,
            tab=tab,
            new_name='bar'
        ))
        send_delta.assert_called()
        delta1 = send_delta.call_args[0][1]
        self.assertEqual(delta1['updateTabs'], {str(tab.id): {'name': 'bar'}})

        send_delta.return_value = async_noop()
        self.run_with_async_db(cmd.backward())
        delta2 = send_delta.call_args[0][1]
        self.assertEqual(delta2['updateTabs'], {str(tab.id): {'name': 'foo'}})

    def test_no_op(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        tab.name = 'foo'
        tab.save(update_fields=['name'])

        cmd = self.run_with_async_db(SetTabNameCommand.create(
            workflow=workflow,
            tab=tab,
            new_name='foo'
        ))
        self.assertIsNone(cmd)
