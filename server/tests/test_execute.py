import asyncio
import contextlib
from unittest.mock import patch
from asgiref.sync import async_to_sync
import pandas as pd
from server.tests.utils import DbTestCase, create_testdata_workflow, \
        load_and_add_module, get_param_by_id_name
from server.models.Commands import ChangeParameterCommand
from server.execute import execute_workflow
from server.modules.types import ProcessResult


table_csv = 'A,B\n1,2\n3,4'
table_dataframe = pd.DataFrame({'A': [1, 3], 'B': [2, 4]})


async def fake_send(*args, **kwargs):
    pass


def cached_render_result_revision_list(workflow):
    return list(workflow.wf_modules.values_list(
        'cached_render_result_delta_id',
        flat=True
    ))


class ExecuteTests(DbTestCase):
    def test_execute_revision_0(self):
        # Don't crash on a new workflow (rev=0, no caches)
        workflow = create_testdata_workflow(table_csv)
        wf_module2 = load_and_add_module('selectcolumns', workflow=workflow)
        async_to_sync(execute_workflow)(workflow)
        wf_module2.refresh_from_db()
        result = wf_module2.get_cached_render_result().result

        self.assertEqual(result, ProcessResult(table_dataframe))
        self.assertEqual(cached_render_result_revision_list(workflow), [0, 0])

    @patch('server.websockets.ws_client_send_delta_async', fake_send)
    def test_execute_new_revision(self):
        workflow = create_testdata_workflow(table_csv)
        wf_module2 = load_and_add_module('selectcolumns', workflow=workflow)

        async_to_sync(execute_workflow)(workflow)

        pval = get_param_by_id_name('colnames', wf_module=wf_module2)
        pval.set_value('A')

        wf_module2.last_relevant_delta_id = 2
        wf_module2.save(update_fields=['last_relevant_delta_id'])

        async_to_sync(execute_workflow)(workflow)

        wf_module2.refresh_from_db()
        result = wf_module2.get_cached_render_result().result

        self.assertEqual(result, ProcessResult(table_dataframe[['A']]))
        self.assertEqual(cached_render_result_revision_list(workflow), [0, 2])

    def test_execute_cache_hit(self):
        workflow = create_testdata_workflow(table_csv)
        wf_module2 = load_and_add_module('selectcolumns', workflow=workflow)

        async_to_sync(execute_workflow)(workflow)
        wf_module2.refresh_from_db()
        result1 = wf_module2.get_cached_render_result().result

        with patch('server.dispatch.module_dispatch_render') as mdr:
            async_to_sync(execute_workflow)(workflow)
            wf_module2.refresh_from_db()
            result2 = wf_module2.get_cached_render_result().result
            self.assertFalse(mdr.called)
            self.assertEqual(result2, result1)

    def test_resume_without_rerunning_unneeded_renders(self):
        workflow = create_testdata_workflow(table_csv)
        wf_module1 = workflow.wf_modules.first()
        wf_module2 = load_and_add_module('selectcolumns', workflow=workflow,
                                         last_relevant_delta_id=1)
        wf_module1.last_relevant_delta_id = 1
        wf_module1.save()

        async_to_sync(execute_workflow)(workflow)

        wf_module2.refresh_from_db()
        expected = wf_module2.get_cached_render_result().result
        wf_module2.last_relevant_delta_id = 2
        wf_module2.save()

        with patch('server.dispatch.module_dispatch_render') as mdr:
            mdr.return_value = expected
            async_to_sync(execute_workflow)(workflow)
            mdr.assert_called_once()
            wf_module2.refresh_from_db()
            result = wf_module2.get_cached_render_result().result
            self.assertEqual(result, expected)
