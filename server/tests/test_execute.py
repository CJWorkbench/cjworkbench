from server.tests.utils import DbTestCase, create_testdata_workflow, \
        load_and_add_module, get_param_by_id_name
from server.models.Commands import ChangeParameterCommand
from server.execute import execute_wfmodule
from server.modules.types import ProcessResult
import pandas as pd
from unittest import mock


table_csv = 'A,B\n1,2\n3,4'
table_dataframe = pd.DataFrame({'A': [1, 3], 'B': [2, 4]})


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
        result = execute_wfmodule(wf_module2)
        self.assertEqual(result, ProcessResult(table_dataframe))
        self.assertEqual(cached_render_result_revision_list(workflow), [0, 0])

    def test_execute_new_revision(self):
        workflow = create_testdata_workflow(table_csv)
        wf_module2 = load_and_add_module('selectcolumns', workflow=workflow)

        # Add command, modifying revision
        pval = get_param_by_id_name('colnames', wf_module=wf_module2)
        ChangeParameterCommand.create(pval, 'A')

        self.assertEqual(cached_render_result_revision_list(workflow),
                         [None, None])

        wf_module1 = workflow.wf_modules.first()
        wf_module1.last_relevant_delta_id = 1
        wf_module1.save()
        wf_module2.last_relevant_delta_id = 2
        wf_module2.save()

        result = execute_wfmodule(wf_module2)
        self.assertEqual(result, ProcessResult(table_dataframe[['A']]))
        self.assertEqual(cached_render_result_revision_list(workflow), [1, 2])

    def test_execute_cache_hit(self):
        workflow = create_testdata_workflow(table_csv)
        wf_module2 = load_and_add_module('selectcolumns', workflow=workflow)
        # Execute -- which should cache the result
        expected = execute_wfmodule(wf_module2)

        with mock.patch('server.dispatch.module_dispatch_render') as mdr:
            result = execute_wfmodule(wf_module2)
            self.assertFalse(mdr.called)
            self.assertEqual(result, expected)

    def test_resume_without_rerunning_unneeded_renders(self):
        workflow = create_testdata_workflow(table_csv)
        wf_module1 = workflow.wf_modules.first()
        wf_module2 = load_and_add_module('selectcolumns', workflow=workflow,
                                         last_relevant_delta_id=1)
        wf_module1.last_relevant_delta_id = 1
        wf_module1.save()

        expected = execute_wfmodule(wf_module2)

        wf_module2.refresh_from_db()
        wf_module2.last_relevant_delta_id = 2
        wf_module2.save()

        with mock.patch('server.dispatch.module_dispatch_render') as mdr:
            mdr.return_value = expected
            result = execute_wfmodule(wf_module2)
            mdr.assert_called_once()
            self.assertEqual(result, expected)
