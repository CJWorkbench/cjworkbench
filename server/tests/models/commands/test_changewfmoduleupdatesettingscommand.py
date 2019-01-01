from unittest.mock import patch
from asgiref.sync import async_to_sync
from django.utils import timezone
from server.models import Workflow
from server.models.commands import ChangeWfModuleUpdateSettingsCommand
from server.tests.utils import DbTestCase


async def async_noop(*args, **kwargs):
    pass


@patch('server.models.Delta.schedule_execute', async_noop)
@patch('server.models.Delta.ws_notify', async_noop)
class ChangeWfModuleUpdateSettingsCommandTests(DbTestCase):
    def test_change_update_settings(self):
        workflow = Workflow.create_and_init()

        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            last_relevant_delta_id=workflow.last_delta_id,
            auto_update_data=False,
            next_update=None,
            update_interval=600
        )

        # do
        mydate = timezone.now()
        cmd = self.run_with_async_db(
            ChangeWfModuleUpdateSettingsCommand.create(
                wf_module,
                True,
                mydate,
                1000
            )
        )
        self.assertTrue(wf_module.auto_update_data)
        self.assertEqual(wf_module.next_update, mydate)
        self.assertEqual(wf_module.update_interval, 1000)
        wf_module.refresh_from_db()
        self.assertTrue(wf_module.auto_update_data)
        self.assertEqual(wf_module.next_update, mydate)
        self.assertEqual(wf_module.update_interval, 1000)

        # undo
        self.run_with_async_db(cmd.backward())
        self.assertFalse(wf_module.auto_update_data)
        self.assertEqual(wf_module.next_update, None)
        self.assertEqual(wf_module.update_interval, 600)
        wf_module.refresh_from_db()
        self.assertFalse(wf_module.auto_update_data)
        self.assertEqual(wf_module.next_update, None)
        self.assertEqual(wf_module.update_interval, 600)

        # redo
        self.run_with_async_db(cmd.forward())
        self.assertTrue(wf_module.auto_update_data)
        self.assertEqual(wf_module.next_update, mydate)
        self.assertEqual(wf_module.update_interval, 1000)
        wf_module.refresh_from_db()
        self.assertTrue(wf_module.auto_update_data)
        self.assertEqual(wf_module.next_update, mydate)
        self.assertEqual(wf_module.update_interval, 1000)
