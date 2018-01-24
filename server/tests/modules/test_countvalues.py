from django.test import TestCase
from server.tests.utils import *
from server.execute import execute_wfmodule

# ---- CountValues ----


class CountValuesTests(LoggedInTestCase):
    def setUp(self):
        super(CountValuesTests, self).setUp()  # log in

        # test data designed to give different output if sorted by freq vs value
        count_csv = 'Month,Amount\nJan,10\nFeb,5\nMar,10\n'
        workflow = create_testdata_workflow(count_csv)

        self.wf_module = load_and_add_module('countvalues', workflow=workflow)
        self.col_pval = get_param_by_id_name('column')
        self.sort_pval = get_param_by_id_name('sortby')
        self.data_pval = get_param_by_id_name('csv')

    def test_render(self):
        # NOP if no column given
        set_string(self.col_pval, '')
        out = execute_wfmodule(self.wf_module)
        self.assertFalse(out.empty)

        # sort by value
        set_string(self.col_pval, 'Amount')
        set_integer(self.sort_pval,0)
        out = execute_wfmodule(self.wf_module)
        self.assertEqual(str(out), '   Amount  count\n0       5      1\n1      10      2')

        # sort by freq
        set_integer(self.sort_pval,1)
        out = execute_wfmodule(self.wf_module)
        self.assertEqual(str(out), '   Amount  count\n0      10      2\n1       5      1' )

        # bad column name should produce error
        set_string(self.col_pval,'hilarious')
        out = execute_wfmodule(self.wf_module)
        self.wf_module.refresh_from_db()
        self.assertEqual(self.wf_module.status, WfModule.ERROR)


