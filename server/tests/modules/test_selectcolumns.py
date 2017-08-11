from django.test import TestCase
from server.tests.utils import *
from server.execute import execute_wfmodule


# ---- SelectColumns ----

class SelectColumnsTests(LoggedInTestCase):
    def setUp(self):
        super(SelectColumnsTests, self).setUp()  # log in
        workflow = create_testdata_workflow()
        module_def = load_module_def('selectcolumns')
        self.wf_module = load_and_add_module(workflow, module_def)
        self.cols_pval = get_param_by_id_name('colnames')

    def test_render(self):
        # select a single column
        self.cols_pval.value = 'Month'
        self.cols_pval.save()
        out = execute_wfmodule(self.wf_module)
        table = mock_csv_table[['Month']]
        self.assertEqual(str(out), str(table))

        # select a single column, with stripped whitespace
        self.cols_pval.value = 'Month '
        self.cols_pval.save()
        out = execute_wfmodule(self.wf_module)
        self.assertEqual(str(out), str(table))

        # reverse column order
        self.cols_pval.value = 'Amount,Month'
        self.cols_pval.save()
        out = execute_wfmodule(self.wf_module)
        table = mock_csv_table[['Amount','Month']]
        self.assertEqual(str(out), str(table))

        # bad column name should produce error
        self.cols_pval.value = 'Amountxxx,Month'
        self.cols_pval.save()
        out = execute_wfmodule(self.wf_module)
        self.wf_module.refresh_from_db()
        self.assertEqual(self.wf_module.status, WfModule.ERROR)


