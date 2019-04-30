import asyncio
import logging
from unittest.mock import patch
from dateutil import parser
from server.cron import autoupdate
from server.models import Workflow
from server.tests.utils import DbTestCase


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


class UpdatesTests(DbTestCase):
    @patch('server.rabbitmq.queue_fetch')
    @patch('server.websockets.ws_client_send_delta_async',
           lambda _1, _2: future_none)
    @patch('django.utils.timezone.now',
           lambda: parser.parse('Aug 28 1999 2:35PM UTC'))
    def test_queue_fetches(self, mock_queue_fetch):
        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)

        # wfm1 does not auto-update
        self.wfm1 = tab.wf_modules.create(order=0, auto_update_data=False)

        # wfm2 is ready to update
        self.wfm2 = tab.wf_modules.create(
            order=1,
            auto_update_data=True,
            last_update_check=parser.parse('Aug 28 1999 2:24PM UTC'),
            next_update=parser.parse('Aug 28 1999 2:34PM UTC'),
            update_interval=600
        )

        # wfm3 has a few more minutes before it should update
        self.wfm3 = tab.wf_modules.create(
            order=2,
            auto_update_data=True,
            last_update_check=parser.parse('Aug 28 1999 2:20PM UTC'),
            next_update=parser.parse('Aug 28 1999 2:40PM UTC'),
            update_interval=1200
        )

        mock_queue_fetch.return_value = future_none

        # eat log messages
        with self.assertLogs(autoupdate.__name__, logging.INFO):
            self.run_with_async_db(
                autoupdate.queue_fetches(SuccessfulRenderLock)
            )

        self.assertEqual(mock_queue_fetch.call_count, 1)
        mock_queue_fetch.assert_called_with(self.wfm2)

        self.wfm2.refresh_from_db()
        self.assertTrue(self.wfm2.is_busy)

        # Second call shouldn't fetch again, because it's busy
        self.run_with_async_db(
            autoupdate.queue_fetches(SuccessfulRenderLock)
        )

        self.assertEqual(mock_queue_fetch.call_count, 1)
