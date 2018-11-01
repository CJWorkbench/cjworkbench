import asyncio
import logging
from unittest.mock import patch
from asgiref.sync import async_to_sync
from dateutil import parser
from server import updates
from server.models import Workflow
from server.tests.utils import DbTestCase, load_module_version


future_none = asyncio.Future()
future_none.set_result(None)


class SuccessfulRenderLock:
    def __init__(self, workflow_id: int):
        self.workflow_id = workflow_id

    @classmethod
    def render_lock(cls, workflow_id: int):
        return cls(workflow_id)

    async def __aenter__(self):
        pass

    async def __aexit__(self, exc_type, exc, tb):
        pass


#class FailedRenderLock:
#    def __init__(self, workflow_id):
#        self.workflow_id = workflow_id
#
#    async def __aenter__(self):
#        raise worker.WorkflowAlreadyLocked
#
#    async def __aexit__(self, exc_type, exc, tb):
#        pass


class UpdatesTests(DbTestCase):
    @patch('server.rabbitmq.queue_fetch')
    @patch('server.websockets.ws_client_wf_module_status_async',
           lambda _1, _2: future_none)
    @patch('django.utils.timezone.now',
           lambda: parser.parse('Aug 28 1999 2:35PM UTC'))
    def test_update_scan(self, mock_queue_fetch):
        self.workflow = Workflow.objects.create()
        self.loadurl = load_module_version('loadurl')
        self.wfm1 = self.workflow.wf_modules.create(
            module_version=self.loadurl,
            order=0
        )
        self.wfm2 = self.workflow.wf_modules.create(
            module_version=self.loadurl,
            order=1
        )
        self.wfm3 = self.workflow.wf_modules.create(
            module_version=self.loadurl,
            order=2
        )

        mock_queue_fetch.return_value = future_none

        # This module does not auto update
        self.wfm1.auto_update_data = False
        self.wfm1.save()

        # This module ready to update
        self.wfm2.auto_update_data = True
        self.wfm2.last_update_check = parser.parse('Aug 28 1999 2:24PM UTC')
        due_for_update = parser.parse('Aug 28 1999 2:34PM UTC')
        self.wfm2.next_update = due_for_update
        self.wfm2.update_interval = 600
        self.wfm2.save()

        # This module still has a few more minutes before it should update
        self.wfm3.auto_update_data = True
        self.wfm3.last_update_check = parser.parse('Aug 28 1999 2:20PM UTC')
        not_due_for_update = parser.parse('Aug 28 1999 2:40PM UTC')
        self.wfm3.next_update = not_due_for_update
        self.wfm3.update_interval = 1200
        self.wfm3.save()

        # eat log messages
        with self.assertLogs(updates.__name__, logging.DEBUG):
            async_to_sync(updates.update_wfm_data_scan)(SuccessfulRenderLock)

        self.assertEqual(mock_queue_fetch.call_count, 1)
        mock_queue_fetch.assert_called_with(self.wfm2)

        self.wfm2.refresh_from_db()
        self.assertTrue(self.wfm2.is_busy)

        # Second call shouldn't fetch again, because it's busy
        with self.assertLogs(updates.__name__, logging.DEBUG):
            async_to_sync(updates.update_wfm_data_scan)(SuccessfulRenderLock)

        self.assertEqual(mock_queue_fetch.call_count, 1)
