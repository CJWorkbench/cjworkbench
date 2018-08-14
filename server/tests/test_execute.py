from server.tests.utils import DbTestCase, create_testdata_workflow, \
        load_and_add_module, get_param_by_id_name
from server.models.Commands import ChangeParameterCommand
from server.execute import execute_wfmodule
from server.modules.types import ProcessResult
import pandas as pd
import io
from unittest import mock


table_csv = 'A,B\n1,2\n3,4'
table_dataframe = pd.DataFrame({'A': [1, 3], 'B': [2, 4]})


def cached_render_result_revision_list(workflow):
    return list(workflow.wf_modules.values_list(
        'cached_render_result_workflow_revision',
        flat=True
    ))


class ExecuteTests(DbTestCase):
    def test_execute_revision_0(self):
        # Don't crash on a new workflow (rev=0, no caches)
        workflow = create_testdata_workflow(table_csv)
        wf_module2 = load_and_add_module('selectcolumns', workflow=workflow)
        self.assertEqual(workflow.revision(), 0)
        result = execute_wfmodule(wf_module2)
        self.assertEqual(workflow.revision(), 0)
        self.assertEqual(result, ProcessResult(table_dataframe))
        self.assertEqual(cached_render_result_revision_list(workflow), [0, 0])

    def test_execute_new_revision(self):
        workflow = create_testdata_workflow(table_csv)
        wf_module2 = load_and_add_module('selectcolumns', workflow=workflow)

        # Add command, modifying revision
        pval = get_param_by_id_name('colnames', wf_module=wf_module2)
        ChangeParameterCommand.create(pval, 'A')

        workflow.refresh_from_db()
        revision = workflow.last_delta_id
        self.assertEqual(workflow.revision(), revision)
        self.assertEqual(cached_render_result_revision_list(workflow),
                         [None, None])
        wf_module2.refresh_from_db()
        result = execute_wfmodule(wf_module2)
        self.assertEqual(result, ProcessResult(table_dataframe[['A']]))
        workflow.refresh_from_db()
        self.assertEqual(workflow.revision(), revision)
        self.assertEqual(cached_render_result_revision_list(workflow),
                         [revision, revision])

    def test_execute_cache_hit(self):
        workflow = create_testdata_workflow(table_csv)
        wf_module2 = load_and_add_module('selectcolumns', workflow=workflow)
        # Execute -- which should cache the result
        expected = execute_wfmodule(wf_module2)

        with mock.patch('server.dispatch.module_dispatch_render') as mdr:
            result = execute_wfmodule(wf_module2)
            self.assertFalse(mdr.called)
            self.assertEqual(result, expected)
