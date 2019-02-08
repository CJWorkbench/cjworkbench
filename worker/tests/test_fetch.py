import asyncio
import logging
from unittest.mock import Mock, patch
from dateutil import parser
from django.contrib.auth.models import User
from django.utils import timezone
import pandas as pd
from pandas.testing import assert_frame_equal
from cjworkbench.types import ProcessResult
from server.models import LoadedModule, ModuleVersion, Workflow
from server.models.commands import InitWorkflowCommand
from server.tests.utils import DbTestCase
from worker import fetch


future_none = asyncio.Future()
future_none.set_result(None)


# Test the scan loop that updates all auto-updating modules
class FetchTests(DbTestCase):
    @patch('server.models.loaded_module.LoadedModule.for_module_version_sync')
    @patch('worker.save.save_result_if_changed')
    def test_fetch_wf_module(self, save_result, load_module):
        result = ProcessResult(pd.DataFrame({'A': [1]}), error='hi')

        async def fake_fetch(*args, **kwargs):
            return result

        fake_module = Mock(LoadedModule)
        load_module.return_value = fake_module
        fake_module.fetch.side_effect = fake_fetch

        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            next_update=parser.parse('Aug 28 1999 2:24PM UTC'),
            update_interval=600
        )

        now = parser.parse('Aug 28 1999 2:24:02PM UTC')
        due_for_update = parser.parse('Aug 28 1999 2:34PM UTC')

        with self.assertLogs(fetch.__name__, logging.DEBUG):
            self.run_with_async_db(fetch.fetch_wf_module(workflow.id,
                                                         wf_module, now))

        save_result.assert_called_with(workflow.id, wf_module, result)

        wf_module.refresh_from_db()
        self.assertEqual(wf_module.last_update_check, now)
        self.assertEqual(wf_module.next_update, due_for_update)

    @patch('server.models.loaded_module.LoadedModule.for_module_version_sync')
    def test_fetch_wf_module_skip_missed_update(self, load_module):
        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        wf_module = tab.wf_modules.create(
            order=0,
            next_update=parser.parse('Aug 28 1999 2:24PM UTC'),
            update_interval=600
        )

        load_module.side_effect = Exception('caught')  # least-code test case

        now = parser.parse('Aug 28 1999 2:34:02PM UTC')
        due_for_update = parser.parse('Aug 28 1999 2:44PM UTC')

        with self.assertLogs(fetch.__name__):
            self.run_with_async_db(fetch.fetch_wf_module(workflow.id,
                                                         wf_module, now))

        wf_module.refresh_from_db()
        self.assertEqual(wf_module.next_update, due_for_update)

    @patch('server.models.loaded_module.LoadedModule.for_module_version_sync')
    def test_crashing_module(self, load_module):
        async def fake_fetch(*args, **kwargs):
            raise ValueError('boo')

        fake_module = Mock(LoadedModule)
        load_module.return_value = fake_module
        fake_module.fetch.side_effect = fake_fetch

        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        wf_module = tab.wf_modules.create(
            order=0,
            next_update=parser.parse('Aug 28 1999 2:24PM UTC'),
            update_interval=600
        )

        now = parser.parse('Aug 28 1999 2:34:02PM UTC')
        due_for_update = parser.parse('Aug 28 1999 2:44PM UTC')

        with self.assertLogs(fetch.__name__, level='ERROR') as cm:
            # We should log the actual error
            self.run_with_async_db(fetch.fetch_wf_module(workflow.id,
                                                         wf_module, now))
            self.assertEqual(cm.records[0].exc_info[0], ValueError)

        wf_module.refresh_from_db()
        # [adamhooper, 2018-10-26] while fiddling with tests, I changed the
        # behavior to record the update check even when module fetch fails.
        # Previously, an exception would prevent updating last_update_check,
        # and I think that must be wrong.
        self.assertEqual(wf_module.last_update_check, now)
        self.assertEqual(wf_module.next_update, due_for_update)

    @patch('server.models.loaded_module.LoadedModule.for_module_version_sync')
    @patch('worker.save.save_result_if_changed')
    def _test_fetch(self, fn, wf_module, save, load) -> ProcessResult:
        """
        Stub out a `fetch` method for `wf_module`.

        Return result.
        """
        if wf_module.module_version is None:
            # White-box: we aren't testing what happens in the (valid) case
            # that a ModuleVersion has been deleted while in use. Pretend it's
            # there.
            wf_module._module_version = ModuleVersion(spec={'parameters': []})

        try:
            workflow_id = wf_module.workflow_id
        except AttributeError:  # No tab/workflow in database
            workflow_id = 1

        # Mock the module we load, so it calls fn() directly.
        load.return_value = LoadedModule('test', '1', False, fetch_impl=fn)
        load.return_value.fetch = fn
        save.return_value = future_none

        # Mock wf_module.save(), which we aren't testing.
        wf_module.save = Mock()

        with self.assertLogs(fetch.__name__, logging.DEBUG):
            self.run_with_async_db(fetch.fetch_wf_module(workflow_id,
                                                         wf_module,
                                                         timezone.now()))

        save.assert_called_once()
        self.assertEqual(save.call_args[0][0], workflow_id)
        self.assertEqual(save.call_args[0][1], wf_module)

        result = save.call_args[0][2]
        return result

    def test_fetch_get_params(self):
        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        ModuleVersion.create_or_replace_from_spec({
            'id_name': 'x',
            'name': 'x',
            'category': 'Clean',
            'parameters': [
                {'id_name': 'foo', 'type': 'string'}
            ]
        })
        wf_module = tab.wf_modules.create(order=0, module_id_name='x',
                                          params={'foo': 'bar'})

        async def fetch(params, **kwargs):
            self.assertEqual(params['foo'], 'bar')

        self._test_fetch(fetch, wf_module)

    def test_fetch_get_workflow_owner(self):
        owner = User.objects.create(username='o', email='o@example.org')
        workflow = Workflow.objects.create(owner=owner)
        tab = workflow.tabs.create(position=0)
        wf_module = tab.wf_modules.create(order=0)

        async def fetch(params, *, get_workflow_owner, **kwargs):
            self.assertEqual(await get_workflow_owner(), owner)

        self._test_fetch(fetch, wf_module)

    def test_fetch_get_workflow_owner_anonymous(self):
        workflow = Workflow.objects.create(owner=None)
        tab = workflow.tabs.create(position=0)
        wf_module = tab.wf_modules.create(order=0)

        async def fetch(params, *, get_workflow_owner, **kwargs):
            self.assertIsNone(await get_workflow_owner())

        self._test_fetch(fetch, wf_module)

    def test_fetch_get_input_dataframe_happy_path(self):
        table = pd.DataFrame({'A': [1]})

        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        delta = InitWorkflowCommand.create(workflow)
        wfm1 = tab.wf_modules.create(order=0,
                                     last_relevant_delta_id=delta.id)
        wfm1.cache_render_result(delta.id, ProcessResult(table))
        wfm1.save()
        wfm2 = tab.wf_modules.create(order=1)

        async def fetch(params, *, get_input_dataframe, **kwargs):
            assert_frame_equal(await get_input_dataframe(), table)

        self._test_fetch(fetch, wfm2)

    def test_fetch_get_input_dataframe_two_tabs(self):
        table = pd.DataFrame({'A': [1]})
        wrong_table = pd.DataFrame({'B': [1]})

        workflow = Workflow.create_and_init()
        delta_id = workflow.last_delta_id
        tab = workflow.tabs.first()
        wfm1 = tab.wf_modules.create(order=0, last_relevant_delta_id=delta_id)
        wfm1.cache_render_result(delta_id, ProcessResult(table))
        wfm2 = tab.wf_modules.create(order=1)

        tab2 = workflow.tabs.create(position=1)
        wfm3 = tab2.wf_modules.create(order=0, last_relevant_delta_id=delta_id)
        wfm3.cache_render_result(delta_id, ProcessResult(wrong_table))

        async def fetch(params, *, get_input_dataframe, **kwargs):
            assert_frame_equal(await get_input_dataframe(), table)

        self._test_fetch(fetch, wfm2)

    def test_fetch_get_input_dataframe_empty_cache(self):
        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        delta = InitWorkflowCommand.create(workflow)
        tab.wf_modules.create(order=0, last_relevant_delta_id=delta.id)
        wfm2 = tab.wf_modules.create(order=1)

        async def fetch(params, *, get_input_dataframe, **kwargs):
            self.assertIsNone(await get_input_dataframe())

        self._test_fetch(fetch, wfm2)

    def test_fetch_get_input_dataframe_stale_cache(self):
        table = pd.DataFrame({'A': [1]})

        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        delta1 = InitWorkflowCommand.create(workflow)
        wfm1 = tab.wf_modules.create(order=0, last_relevant_delta_id=delta1.id)
        wfm1.cache_render_result(delta1.id, ProcessResult(table))

        # Now make wfm1's output stale
        delta2 = InitWorkflowCommand.create(workflow)
        wfm1.last_relevant_delta_id = delta2.id
        wfm1.save(update_fields=['last_relevant_delta_id'])

        wfm2 = tab.wf_modules.create(order=1)

        async def fetch(params, *, get_input_dataframe, **kwargs):
            self.assertIsNone(await get_input_dataframe())

        self._test_fetch(fetch, wfm2)

    def test_fetch_get_input_dataframe_race_delete_prior_wf_module(self):
        table = pd.DataFrame({'A': [1]})

        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        delta = InitWorkflowCommand.create(workflow)
        wfm1 = tab.wf_modules.create(order=0, last_relevant_delta_id=delta.id)
        wfm1.cache_render_result(delta.id, ProcessResult(table))
        wfm1.save()
        wfm2 = tab.wf_modules.create(order=1)

        # Delete from the database. They're still in memory. This deletion can
        # happen on production: we aren't locking the workflow during fetch
        # (because it's far too slow).
        wfm1.delete()

        async def fetch(params, *, get_input_dataframe, **kwargs):
            self.assertIsNone(await get_input_dataframe())

        self._test_fetch(fetch, wfm2)

    def test_fetch_get_input_dataframe_race_delete_workflow(self):
        table = pd.DataFrame({'A': [1]})

        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        delta = InitWorkflowCommand.create(workflow)
        wfm1 = tab.wf_modules.create(order=0, last_relevant_delta_id=delta.id)
        wfm1.cache_render_result(delta.id, ProcessResult(table))
        wfm1.save()
        wfm2 = tab.wf_modules.create(order=1)

        # Delete from the database. They're still in memory. This deletion can
        # happen on production: we aren't locking the workflow during fetch
        # (because it's far too slow).
        workflow.delete()

        async def fetch(params, *, get_input_dataframe, **kwargs):
            self.assertIsNone(await get_input_dataframe())

        self._test_fetch(fetch, wfm2)

    def test_fetch_get_stored_dataframe_happy_path(self):
        table = pd.DataFrame({'A': [1]})

        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        wf_module = tab.wf_modules.create(order=0)
        wf_module.stored_data_version = wf_module.store_fetched_table(table)
        wf_module.save()

        async def fetch(params, *, get_stored_dataframe, **kwargs):
            assert_frame_equal(await get_stored_dataframe(), table)

        self._test_fetch(fetch, wf_module)

    def test_fetch_get_stored_dataframe_no_stored_data_frame(self):
        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        wf_module = tab.wf_modules.create(order=0)

        async def fetch(params, *, get_stored_dataframe, **kwargs):
            self.assertIsNone(await get_stored_dataframe())

        self._test_fetch(fetch, wf_module)

    def test_fetch_get_stored_dataframe_race_delete_wf_module(self):
        table = pd.DataFrame({'A': [1]})

        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        wf_module = tab.wf_modules.create(order=0)
        wf_module.stored_data_version = wf_module.store_fetched_table(table)
        wf_module.save()

        # Delete from the database. They're still in memory. This deletion can
        # happen on production: we aren't locking the workflow during fetch
        # (because it's far too slow).
        wf_module.delete()
        wf_module.id = 3  # simulate race: id is non-empty

        async def fetch(params, *, get_stored_dataframe, **kwargs):
            self.assertIsNone(await get_stored_dataframe())

        self._test_fetch(fetch, wf_module)

    def test_fetch_workflow_id(self):
        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        wf_module = tab.wf_modules.create(order=0)

        async def fetch(params, *, workflow_id, **kwargs):
            self.assertEqual(workflow_id, workflow.id)

        self._test_fetch(fetch, wf_module)
