import io
from django.test import TestCase, override_settings
import pandas as pd
from server.tests.utils import add_new_workflow, load_and_add_module, \
        get_param_by_id_name, mock_csv_table, add_new_wf_module
from server.dispatch import module_dispatch_render
from server.modules.types import ProcessResult


class DispatchTests(TestCase):
    # Test workflow with modules that implement a simple pipeline on test data
    def setUp(self):
        super(DispatchTests, self).setUp()  # log in

        self.test_csv = 'Class,M,F\n' \
                        'math,10,12\n' \
                        'english,,7\n' \
                        'history,11,13\n' \
                        'economics,20,20'
        self.test_table = pd.read_csv(io.StringIO(self.test_csv))
        self.test_table_MF = self.test_table[['M', 'F']]

        self.workflow = add_new_workflow('dispatch tests wf')
        self.wfm = load_and_add_module('selectcolumns', workflow=self.workflow)
        get_param_by_id_name('colnames').set_value('M,F')

    # basic internal render test
    def test_internal_render(self):
        result = module_dispatch_render(self.wfm, self.test_table)
        self.assertEqual(result, ProcessResult(self.test_table_MF))

    def test_external_render(self):
        # External modules take a different code path,
        # but this is tested in test_importfromgithub.test_load_and_dispatch
        pass

    # TODO single column parameter sanitize test
    # don't crash when passing multicolumn parameter which contains
    # non-existent colnames
    def test_multicolumn_sanitize(self):
        # no M,F cols
        result = module_dispatch_render(self.wfm, mock_csv_table)
        self.assertEqual(result, ProcessResult(pd.DataFrame([{}, {}])))

    # should return empty table if module is missing (not, for example, None)
    def test_missing_module(self):
        workflow = add_new_workflow('Missing module')
        wfm = add_new_wf_module(workflow, None, 0)
        result = module_dispatch_render(wfm, mock_csv_table)
        self.assertEqual(result, ProcessResult())

    # None input table should be silently replaced with empty df
    def test_none_table_render(self):
        result = module_dispatch_render(self.wfm, pd.DataFrame())
        self.assertEqual(result, ProcessResult())

    def test_error_render(self):
        # Force an error, ensure that it's returned and the output is a NOP
        wfm = load_and_add_module('pythoncode', workflow=self.workflow)
        code_pval = get_param_by_id_name('code')
        code_pval.set_value('not python code')

        result = module_dispatch_render(wfm, self.test_table)
        self.assertEqual(result, ProcessResult(
            error='Line 1: invalid syntax (user input, line 1)',
            json={'output': ''}  # not part of this test
        ))

    @override_settings(MAX_ROWS_PER_TABLE=2)
    def test_render_static_truncates_table(self):
        table = pd.DataFrame({'a': [1, 2, 3]})
        wfm = load_and_add_module('editcells')  # it never changes row count
        result = module_dispatch_render(wfm, table)
        self.assertEqual(result, ProcessResult(
            dataframe=pd.DataFrame({'a': [1, 2]}),
            error='Truncated output from 3 rows to 2'
        ))
        wfm.refresh_from_db()
