import asyncio
from unittest.mock import Mock, patch
import pandas as pd
from server.tests.utils import DbTestCase
from server.models import LoadedModule, Workflow
from server.models.commands import InitWorkflowCommand
from server.modules.types import ProcessResult
from worker.execute import execute_workflow, UnneededExecution


table_csv = 'A,B\n1,2\n3,4'
table_dataframe = pd.DataFrame({'A': [1, 3], 'B': [2, 4]})


future_none = asyncio.Future()
future_none.set_result(None)


async def fake_send(*args, **kwargs):
    pass


def cached_render_result_revision_list(workflow):
    return list(workflow.tabs.first().live_wf_modules.values_list(
        'cached_render_result_delta_id',
        flat=True
    ))


class ExecuteTests(DbTestCase):
    def _execute(self, workflow):
        self.run_with_async_db(execute_workflow(workflow,
                                                workflow.last_delta_id))

    @patch('server.models.loaded_module.LoadedModule.for_module_version_sync')
    @patch('server.websockets.ws_client_send_delta_async', fake_send)
    def test_execute_new_revision(self, fake_load_module):
        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        delta1 = InitWorkflowCommand.create(workflow)
        wf_module = tab.wf_modules.create(
            order=1,
            last_relevant_delta_id=delta1.id
        )

        result1 = ProcessResult(pd.DataFrame({'A': [1]}))
        wf_module.cache_render_result(delta1.id, result1)

        result2 = ProcessResult(pd.DataFrame({'B': [2]}))
        delta2 = InitWorkflowCommand.create(workflow)
        wf_module.last_relevant_delta_id = delta2.id
        wf_module.save(update_fields=['last_relevant_delta_id'])

        fake_module = Mock(LoadedModule)
        fake_load_module.return_value = fake_module
        fake_module.render.return_value = result2

        self._execute(workflow)

        wf_module.refresh_from_db()
        self.assertEqual(wf_module.cached_render_result.result, result2)

    @patch('server.models.loaded_module.LoadedModule.for_module_version_sync')
    def test_execute_race_delete_workflow(self, fake_load_module):
        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        delta = InitWorkflowCommand.create(workflow)
        tab.wf_modules.create(
            order=0,
            last_relevant_delta_id=delta.id
        )
        tab.wf_modules.create(
            order=1,
            last_relevant_delta_id=delta.id
        )

        def load_module_and_delete(module_version):
            workflow.delete()
            fake_module = Mock(LoadedModule)
            result = ProcessResult(pd.DataFrame({'A': [1]}))
            fake_module.render.return_value = result
            return fake_module
        fake_load_module.side_effect = load_module_and_delete

        with self.assertRaises(UnneededExecution):
            self._execute(workflow)

    @patch('server.models.loaded_module.LoadedModule.for_module_version_sync')
    @patch('server.websockets.ws_client_send_delta_async')
    def test_execute_mark_unreachable(self, send_delta_async,
                                      fake_load_module):
        send_delta_async.return_value = future_none

        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        delta = InitWorkflowCommand.create(workflow)
        wf_module1 = tab.wf_modules.create(
            order=0,
            last_relevant_delta_id=delta.id
        )
        wf_module2 = tab.wf_modules.create(
            order=1,
            last_relevant_delta_id=delta.id
        )
        wf_module3 = tab.wf_modules.create(
            order=2,
            last_relevant_delta_id=delta.id
        )

        fake_module = Mock(LoadedModule)
        fake_load_module.return_value = fake_module
        fake_module.render.return_value = ProcessResult(error='foo')

        self._execute(workflow)

        wf_module1.refresh_from_db()
        self.assertEqual(wf_module1.cached_render_result.status, 'error')
        self.assertEqual(wf_module1.cached_render_result.result,
                         ProcessResult(error='foo'))

        wf_module2.refresh_from_db()
        self.assertEqual(wf_module2.cached_render_result.status,
                         'unreachable')
        self.assertEqual(wf_module2.cached_render_result.result,
                         ProcessResult())

        wf_module3.refresh_from_db()
        self.assertEqual(wf_module3.cached_render_result.status,
                         'unreachable')
        self.assertEqual(wf_module3.cached_render_result.result,
                         ProcessResult())

        send_delta_async.assert_called_with(workflow.id, {
            'updateWfModules': {
                str(wf_module3.id): {
                    'output_status': 'unreachable',
                    'quick_fixes': [],
                    'output_error': '',
                    'output_columns': [],
                    'output_n_rows': 0,
                    'cached_render_result_delta_id': delta.id,
                }
            }
        })

    @patch('server.models.loaded_module.LoadedModule.for_module_version_sync')
    @patch('server.websockets.ws_client_send_delta_async', fake_send)
    def test_execute_cache_hit(self, fake_module):
        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        delta = InitWorkflowCommand.create(workflow)
        wf_module1 = tab.wf_modules.create(
            order=0,
            last_relevant_delta_id=delta.id
        )
        result1 = ProcessResult(pd.DataFrame({'A': [1]}))
        wf_module1.cache_render_result(delta.id, result1)
        wf_module2 = tab.wf_modules.create(
            order=1,
            last_relevant_delta_id=delta.id
        )
        result2 = ProcessResult(pd.DataFrame({'B': [2]}))
        wf_module2.cache_render_result(delta.id, result2)

        fake_module.assert_not_called()

    @patch('server.models.loaded_module.LoadedModule.for_module_version_sync')
    @patch('server.websockets.ws_client_send_delta_async', fake_send)
    def test_resume_without_rerunning_unneeded_renders(self, fake_load_module):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        delta_id = workflow.last_delta_id

        # wf_module1: has a valid, cached result
        wf_module1 = tab.wf_modules.create(
            order=0,
            last_relevant_delta_id=delta_id
        )
        result1 = ProcessResult(pd.DataFrame({'A': [1]}))
        wf_module1.cache_render_result(delta_id, result1)

        # wf_module2: has no cached result (must be rendered)
        wf_module2 = tab.wf_modules.create(
            order=1,
            last_relevant_delta_id=delta_id
        )

        fake_loaded_module = Mock(LoadedModule)
        fake_load_module.return_value = fake_loaded_module
        result2 = ProcessResult(pd.DataFrame({'A': [2]}))
        fake_loaded_module.render.return_value = result2

        self._execute(workflow)

        wf_module2.refresh_from_db()
        actual = wf_module2.cached_render_result.result
        self.assertEqual(actual, result2)
        fake_loaded_module.render.assert_called_once()  # only with module2

    @patch('server.models.loaded_module.LoadedModule.for_module_version_sync')
    @patch('server.websockets.ws_client_send_delta_async', fake_send)
    @patch('server.notifications.email_output_delta')
    def test_email_delta(self, email, fake_load_module):
        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        delta1 = InitWorkflowCommand.create(workflow)
        wf_module = tab.wf_modules.create(
            order=0,
            last_relevant_delta_id=delta1.id,
            notifications=True
        )
        wf_module.cache_render_result(
            delta1.id,
            ProcessResult(pd.DataFrame({'A': [1]}))
        )

        # Now make a new delta, so we need to re-render. The render function's
        # output won't change.
        delta2 = InitWorkflowCommand.create(workflow)
        wf_module.last_relevant_delta_id = delta2.id
        wf_module.save(update_fields=['last_relevant_delta_id'])

        fake_loaded_module = Mock(LoadedModule)
        fake_load_module.return_value = fake_loaded_module
        result2 = ProcessResult(pd.DataFrame({'A': [2]}))
        fake_loaded_module.render.return_value = result2

        self._execute(workflow)

        email.assert_called()

    @patch('server.models.loaded_module.LoadedModule.for_module_version_sync')
    @patch('server.websockets.ws_client_send_delta_async', fake_send)
    @patch('server.notifications.email_output_delta')
    def test_email_no_delta_when_not_changed(self, email, fake_load_module):
        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        delta1 = InitWorkflowCommand.create(workflow)
        wf_module = tab.wf_modules.create(
            order=0,
            last_relevant_delta_id=delta1.id,
            notifications=True
        )
        wf_module.cache_render_result(
            delta1.id,
            ProcessResult(pd.DataFrame({'A': [1]}))
        )

        # Now make a new delta, so we need to re-render. The render function's
        # output won't change.
        delta2 = InitWorkflowCommand.create(workflow)
        wf_module.last_relevant_delta_id = delta2.id
        wf_module.save(update_fields=['last_relevant_delta_id'])

        fake_loaded_module = Mock(LoadedModule)
        fake_load_module.return_value = fake_loaded_module
        result2 = ProcessResult(pd.DataFrame({'A': [1]}))
        fake_loaded_module.render.return_value = result2

        self._execute(workflow)

        email.assert_not_called()
