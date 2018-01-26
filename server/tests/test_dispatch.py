from django.test import TestCase
from server.tests.utils import *
from server.dispatch import module_dispatch_render
import pandas as pd
import io

class DispatchTests(TestCase):

    # Test workflow with modules that implement a simple pipeline on test data
    def setUp(self):
        super(DispatchTests, self).setUp()  # log in

        test_csv = 'Class,M,F\n' \
                   'math,10,12\n' \
                   'english,,7\n' \
                   'history,11,13\n' \
                   'economics,20,20'
        self.test_table = pd.read_csv(io.StringIO(test_csv))
        self.test_table_M = pd.DataFrame(self.test_table['M'])  # need DataFrame ctor otherwise we get series not df
        self.test_table_MF = self.test_table[['M', 'F']]

        # workflow pastes a CSV in then picks columns (by default all columns as cols_pval is empty)
        self.workflow = create_testdata_workflow(test_csv)
        self.wfm1 = WfModule.objects.get()

    def test_basic_internal_render(self):
        out = module_dispatch_render(self.wfm1, pd.DataFrame())
        self.assertTrue(out.equals(self.test_table))

    def test_error_render(self):
        # Force an error, ensure that it's returned and the output is a NOP
        wfm = load_and_add_module('pythoncode', workflow=self.workflow)
        code_pval = get_param_by_id_name('code')
        code_pval.set_value('not python code')

        out = module_dispatch_render(wfm, self.test_table)
        wfm.refresh_from_db()
        self.assertTrue(wfm.status == WfModule.ERROR)
        self.assertTrue(out.equals(self.test_table))

