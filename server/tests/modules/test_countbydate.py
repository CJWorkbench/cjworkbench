from django.test import TestCase
from server.tests.utils import *
from server.execute import execute_wfmodule

# ---- CountByDate ----


class CountValuesTests(LoggedInTestCase):
    def setUp(self):
        super(CountValuesTests, self).setUp()  # log in

        # test data designed to give different output if sorted by freq vs value
        count_csv = 'Date,Amount,Foo\nJan 10 2016,10,Foo\nJul 25 2011,5,Goo\nJan 10 2016,1,Hoo\n'
        workflow = create_testdata_workflow(count_csv)

        module_def = load_module_def('countbydate')
        self.wf_module = load_and_add_module(workflow, module_def)
        self.col_pval = get_param_by_id_name('column')
        self.sort_pval = get_param_by_id_name('sortby')

    def test_render(self):
        # sort by value.
        # Use out.to_csv() instead of str(out) to ensure rows are output in index order (otherwise variable)
        set_string(self.col_pval, 'Date')
        set_integer(self.sort_pval,0)  # 0 = sort by value
        out = execute_wfmodule(self.wf_module)
        self.assertEqual(out.to_csv(index=False), 'date,count\n2011-07-25,1\n2016-01-10,2\n' )

        # sort by freq
        set_integer(self.sort_pval,1)  # 1 = sort by freq
        out = execute_wfmodule(self.wf_module)
        self.assertEqual(out.to_csv(index=False), 'date,count\n2016-01-10,2\n2011-07-25,1\n')

    def test_bad_colname(self):
        # No output if no column given
        set_string(self.col_pval, '')
        out = execute_wfmodule(self.wf_module)
        self.assertTrue(out.empty)

        # bad column name should produce error
        set_string(self.col_pval,'hilarious')
        out = execute_wfmodule(self.wf_module)
        self.wf_module.refresh_from_db()
        self.assertEqual(self.wf_module.status, WfModule.ERROR)

    def test_bad_dates(self):
        # integers are not dates
        set_string(self.col_pval,'Amount')
        out = execute_wfmodule(self.wf_module)
        self.wf_module.refresh_from_db()
        self.assertEqual(self.wf_module.status, WfModule.ERROR)

        # Weird strings are not dates (different error code path)
        set_string(self.col_pval, 'Foo')
        out = execute_wfmodule(self.wf_module)
        self.wf_module.refresh_from_db()
        self.assertEqual(self.wf_module.status, WfModule.ERROR)

