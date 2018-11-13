import logging
from unittest.mock import Mock, patch
from asgiref.sync import async_to_sync
from dateutil import parser
import pandas as pd
from server import worker
from server.models import LoadedModule, Workflow
from server.modules.types import ProcessResult
from server.tests.utils import DbTestCase
from server.worker import fetch


# Test the scan loop that updates all auto-updating modules
class FetchTests(DbTestCase):
    def setUp(self):
        super().setUp()

        self.workflow = Workflow.objects.create()
        self.wf_module = self.workflow.wf_modules.create(order=0)

    @patch('server.models.loaded_module.LoadedModule.for_module_version_sync')
    @patch('server.worker.save.save_result_if_changed')
    def test_fetch_wf_module(self, save_result, load_module):
        result = ProcessResult(pd.DataFrame({'A': [1]}), error='hi')

        async def fake_fetch(*args, **kwargs):
            return result

        fake_module = Mock(LoadedModule)
        load_module.return_value = fake_module
        fake_module.fetch.side_effect = fake_fetch

        self.wf_module.next_update = parser.parse('Aug 28 1999 2:24PM UTC')
        self.wf_module.update_interval = 600
        self.wf_module.save()

        now = parser.parse('Aug 28 1999 2:24:02PM UTC')
        due_for_update = parser.parse('Aug 28 1999 2:34PM UTC')

        with self.assertLogs(fetch.__name__, logging.DEBUG):
            async_to_sync(fetch.fetch_wf_module)(self.wf_module, now)

        save_result.assert_called_with(self.wf_module, result)

        self.wf_module.refresh_from_db()
        self.assertEqual(self.wf_module.last_update_check, now)
        self.assertEqual(self.wf_module.next_update, due_for_update)

    @patch('server.models.loaded_module.LoadedModule.for_module_version_sync')
    def test_fetch_wf_module_skip_missed_update(self, load_module):
        self.wf_module.next_update = parser.parse('Aug 28 1999 2:24PM UTC')
        self.wf_module.update_interval = 600
        self.wf_module.save()

        load_module.side_effect = Exception('caught')  # least-code test case

        now = parser.parse('Aug 28 1999 2:34:02PM UTC')
        due_for_update = parser.parse('Aug 28 1999 2:44PM UTC')

        with self.assertLogs(fetch.__name__):
            async_to_sync(fetch.fetch_wf_module)(self.wf_module, now)

        self.wf_module.refresh_from_db()
        self.assertEqual(self.wf_module.next_update, due_for_update)

    @patch('server.models.loaded_module.LoadedModule.for_module_version_sync')
    def test_crashing_module(self, load_module):
        async def fake_fetch(*args, **kwargs):
            raise ValueError('boo')

        fake_module = Mock(LoadedModule)
        load_module.return_value = fake_module
        fake_module.fetch.side_effect = fake_fetch

        self.wf_module.next_update = parser.parse('Aug 28 1999 2:24PM UTC')
        self.wf_module.update_interval = 600
        self.wf_module.save()

        now = parser.parse('Aug 28 1999 2:34:02PM UTC')
        due_for_update = parser.parse('Aug 28 1999 2:44PM UTC')

        with self.assertLogs(fetch.__name__, level='ERROR') as cm:
            # We should log the actual error
            async_to_sync(fetch.fetch_wf_module)(self.wf_module, now)
            self.assertEqual(cm.records[0].exc_info[0], ValueError)

        self.wf_module.refresh_from_db()
        # [adamhooper, 2018-10-26] while fiddling with tests, I changed the
        # behavior to record the update check even when module fetch fails.
        # Previously, an exception would prevent updating last_update_check,
        # and I think that must be wrong.
        self.assertEqual(self.wf_module.last_update_check, now)
        self.assertEqual(self.wf_module.next_update, due_for_update)

