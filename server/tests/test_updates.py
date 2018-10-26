import asyncio
from datetime import timedelta
import logging
from unittest.mock import patch
from asgiref.sync import async_to_sync
from dateutil import parser
from server import updates
from server.updates import update_wfm_data_scan, update_wf_module
from server.tests.utils import LoggedInTestCase, add_new_workflow, \
        load_module_version, add_new_wf_module


# Mock fetch by making it return None, asynchronously
future_none = asyncio.Future()
future_none.set_result(None)


# Test the scan loop that updates all auto-updating modules
class UpdatesTests(LoggedInTestCase):
    def setUp(self):
        super(UpdatesTests, self).setUp()  # log in

        self.workflow = add_new_workflow('Update scan')
        self.loadurl = load_module_version('loadurl')
        self.wfm1 = add_new_wf_module(self.workflow, self.loadurl, order=0)

    @patch('server.rabbitmq.queue_fetch')
    @patch('django.utils.timezone.now')
    def test_update_scan(self, mock_now, mock_queue_fetch):
        self.wfm2 = add_new_wf_module(self.workflow, self.loadurl, order=1)
        self.wfm3 = add_new_wf_module(self.workflow, self.loadurl, order=2)

        nowtime = parser.parse('Aug 28 1999 2:35PM UTC')
        mock_now.return_value = nowtime
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
            async_to_sync(update_wfm_data_scan)()

        self.assertEqual(mock_queue_fetch.call_count, 1)
        mock_queue_fetch.assert_called_with(self.wfm2)

        self.wfm2.refresh_from_db()
        self.assertTrue(self.wfm2.is_busy)

        # Second call shouldn't fetch again, because it's busy
        with self.assertLogs(updates.__name__, logging.DEBUG):
            async_to_sync(update_wfm_data_scan)()

        self.assertEqual(mock_queue_fetch.call_count, 1)

    @patch('server.updates.module_dispatch_fetch')
    def test_update_wf_module(self, mock_dispatch):
        mock_dispatch.return_value = future_none

        self.wfm1.next_update = parser.parse('Aug 28 1999 2:24PM UTC')
        self.wfm1.update_interval = 600
        self.wfm1.save()

        now = parser.parse('Aug 28 1999 2:24:02PM UTC')
        due_for_update = parser.parse('Aug 28 1999 2:34PM UTC')

        with self.assertLogs(updates.__name__, logging.DEBUG):
            async_to_sync(update_wf_module)(self.wfm1, now)

        mock_dispatch.assert_called_with(self.wfm1)

        self.wfm1.refresh_from_db()
        self.assertEqual(self.wfm1.last_update_check, now)
        self.assertEqual(self.wfm1.next_update, due_for_update)

    @patch('server.updates.module_dispatch_fetch')
    def test_update_wf_module_skip_missed_update(self, mock_dispatch):
        mock_dispatch.return_value = future_none

        self.wfm1.next_update = parser.parse('Aug 28 1999 2:24PM UTC')
        self.wfm1.update_interval = 600
        self.wfm1.save()

        now = parser.parse('Aug 28 1999 2:34:02PM UTC')
        due_for_update = parser.parse('Aug 28 1999 2:44PM UTC')

        with self.assertLogs(updates.__name__, logging.DEBUG):
            async_to_sync(update_wf_module)(self.wfm1, now)

        self.wfm1.refresh_from_db()
        self.assertEqual(self.wfm1.next_update, due_for_update)

    @patch('server.updates.module_dispatch_fetch')
    def test_crashing_module(self, mock_dispatch):
        # Mocked return values. First call raises exception.
        mock_dispatch.side_effect = [Exception('Totes crashed'), future_none]

        self.wfm1.next_update = parser.parse('Aug 28 1999 2:24PM UTC')
        self.wfm1.update_interval = 600
        self.wfm1.save()

        now = parser.parse('Aug 28 1999 2:34:02PM UTC')
        due_for_update = parser.parse('Aug 28 1999 2:44PM UTC')

        with self.assertLogs(updates.__name__, logging.DEBUG):
            async_to_sync(update_wf_module)(self.wfm1, now)

        self.wfm1.refresh_from_db()
        # [adamhooper, 2018-10-26] while fiddling with tests, I changed the
        # behavior to record the update check even when module fetch fails.
        # Previously, an exception would prevent updating last_update_check,
        # and I think that must be wrong.
        self.assertEqual(self.wfm1.last_update_check, now)
        self.assertEqual(self.wfm1.next_update, due_for_update)
