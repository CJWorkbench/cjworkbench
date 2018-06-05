from django.test import TestCase
from django.conf import settings
from server.tests.utils import *
from server.dispatch import module_dispatch_render
import pandas as pd
import numpy as np
import io

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
        out = module_dispatch_render(self.wfm, self.test_table)
        self.assertTrue(out.equals(self.test_table_MF))


    def test_external_render(self):
        # External modules take a different code path,
        # but this is tested in test_importfromgithub.test_load_and_dispatch
        pass


    # TODO single column parameter sanitize test


    # don't crash when passing multicolumn parameter which contains non-existent colnames
    def test_multicolumn_sanitize(self):
        out = module_dispatch_render(self.wfm, mock_csv_table) # no M,F cols
        self.assertTrue(out.empty)

    # should return empty table if module is missing (not, for example, None)
    def test_missing_module(self):
        workflow = add_new_workflow('Missing module')
        wfm = add_new_wf_module(workflow, None, 0)
        out = module_dispatch_render(wfm, mock_csv_table)
        self.assertTrue(out.empty)

    # None input table should be silently replaced with empty df
    def test_none_table_render(self):
        out = module_dispatch_render(self.wfm, pd.DataFrame())
        self.assertTrue(out.empty)

    def test_error_render(self):
        # Force an error, ensure that it's returned and the output is a NOP
        wfm = load_and_add_module('pythoncode', workflow=self.workflow)
        code_pval = get_param_by_id_name('code')
        code_pval.set_value('not python code')

        out = module_dispatch_render(wfm, self.test_table)
        wfm.refresh_from_db()
        self.assertTrue(wfm.status == WfModule.ERROR)
        self.assertEqual(
            wfm.error_msg,
            'invalid syntax (<string>, line 2) at line 1'
        )
        self.assertTrue(out.equals(self.test_table))

    def test_table_truncation(self):
        nrows = settings.MAX_ROWS_PER_TABLE + 1
        bigtable = pd.DataFrame(np.random.randint(0,100,size=(nrows, 4)), columns=list('ABCD'))
        wfm = load_and_add_module('editcells')  # because it never changes row count
        out = module_dispatch_render(wfm, bigtable)
        self.assertTrue(len(out) == settings.MAX_ROWS_PER_TABLE)
        self.assertEqual(wfm.status, WfModule.ERROR)
