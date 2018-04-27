from server.tests.utils import *
from server.updates import update_wfm_data_scan
from server import dispatch
from unittest.mock import MagicMock, patch
from django.utils import timezone
from dateutil import parser
from datetime import timedelta
import logging

# Test the scan loop that updates all auto-updating modules
class UpdatesTests(LoggedInTestCase):

    def setUp(self):
        super(UpdatesTests, self).setUp()  # log in

        self.workflow = add_new_workflow('Update scan')
        loadurl = load_module_version('loadurl')
        self.wfm1 = add_new_wf_module(self.workflow, loadurl, order=0)
        self.wfm2 = add_new_wf_module(self.workflow, loadurl, order=1)
        self.wfm3 = add_new_wf_module(self.workflow, loadurl, order=2)

        # fake out the current time so we can run the test just-so
        self.nowtime = parser.parse('Aug 28 1999 2:35PM UTC')

        # several tests log exceptions or print status, but don't print that every test
        logging.disable(logging.CRITICAL)


    @patch('server.updates.module_dispatch_event')
    @patch('server.updates.timezone.now')
    def test_update_scan(self, mock_now, mock_dispatch):
        mock_now.return_value = self.nowtime

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

        mock_request = {}
        update_wfm_data_scan(mock_request)

        # only wfm2 should have been updated, to update ten minutes from now
        self.assertEqual(mock_dispatch.call_count,1)
        self.assertTrue(mock_dispatch.call_args == ((self.wfm2,),{'request':mock_request}))  # module_dispatch_event(wfm, request) call
        self.wfm2.refresh_from_db()
        self.assertEqual(self.wfm2.last_update_check, self.nowtime)
        self.assertEqual(self.wfm2.next_update, due_for_update + timedelta(seconds=600))

        # wfm1, wfm3 should not have updates
        self.assertEqual(self.wfm3.next_update, not_due_for_update)


    @patch('server.updates.module_dispatch_event')
    @patch('server.updates.timezone.now')
    def test_crashing_module(self, mock_now, mock_dispatch):
        mock_now.return_value = self.nowtime

        # When a module throws an exception, it should get updated to the correct time
        # and all others should still be called

        # Mocked return values. First call raises exception.
        mock_dispatch.side_effect = [Exception('Totes crashed'), None]

        # Ready to update, will crash
        self.wfm1.auto_update_data = True
        last_update1 = parser.parse('Aug 28 1999 2:24PM UTC')
        self.wfm1.last_update_check = last_update1
        self.wfm1.next_update = parser.parse('Aug 28 1999 2:34PM UTC')
        self.wfm1.update_interval = 600
        self.wfm1.save()

        # Ready to update, will not crash
        self.wfm2.auto_update_data = True
        self.wfm2.last_update_check = parser.parse('Aug 28 1999 2:22PM UTC')
        due_for_update = parser.parse('Aug 28 1999 2:32PM UTC')
        self.wfm2.next_update = due_for_update
        self.wfm2.update_interval = 600
        self.wfm2.save()

        mock_request = {}
        update_wfm_data_scan(mock_request)

        # First module should not have updated, but both should have next update time incremented
        self.assertEqual(mock_dispatch.call_count,2)

        self.wfm1.refresh_from_db()
        self.assertEqual(self.wfm1.last_update_check, last_update1)     # unchanged, we crashed
        self.assertTrue(self.wfm1.next_update > self.nowtime)           # changed

        self.wfm2.refresh_from_db()
        self.assertEqual(self.wfm2.last_update_check, self.nowtime)     # changed
        self.assertTrue(self.wfm2.next_update > self.nowtime)           # changed

        logging.disable(logging.NOTSET)

