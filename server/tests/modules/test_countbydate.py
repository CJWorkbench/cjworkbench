from django.test import TestCase
from server.tests.utils import *
from server.execute import execute_wfmodule

# ---- CountByDate ----


class CountValuesTests(LoggedInTestCase):
    def setUp(self):
        super(CountValuesTests, self).setUp()  # log in

        # test data designed to give different output if sorted by freq vs value
        self.count_csv = 'Date,Amount,Foo\nJan 10 2011,10,Foo\nJul 25 2016,5,Goo\n2011-01-10T01:00:00.000,1,Hoo\nJan 10 2011 00:00:01,1,Hoo\nJan 10 2011 00:00:01,1,Hoo\nJan 10 2011 00:01:00,1,Hoo\nJan 15 2011,1,Too\n'
        self.count_csv_time = 'Date,Amount,Foo\n11:00,10,Foo\n12:00,5,Goo\n01:00:00,1,Hoo\n00:00:01,1,Hoo\n00:00:01,1,Hoo\n00:01:00,1,Hoo\nDecember 15 2017 11:05,1,Too\n'
        self.count_csv_dates = 'Date,Amount,Foo\nJan 10 2011,10,Foo\nJul 25 2016,5,Goo\nJan 10 2011,1,Hoo\nJan 10 2011,1,Hoo\nJan 10 2011,1,Hoo\nJan 10 2011,1,Hoo\nJan 15 2011 6:00pm,1,Too\n'
        self.count_timestamps = 'Date,Amount,Foo\n1294617600,10,Foo\n1469404800,5,Goo\n1294621200,1,Hoo\n1294617601,1,Hoo\n1294617601,1,Hoo\n1294617661,1,Hoo\n1295071201,1,Too\n'

        workflow = create_testdata_workflow(self.count_csv)

        self.wf_module = load_and_add_module('countbydate', workflow=workflow)
        self.col_pval = get_param_by_id_name('column')
        self.group_pval = get_param_by_id_name('groupby')
        self.operation_pval = get_param_by_id_name('operation')
        self.target_pval = get_param_by_id_name('targetcolumn')
        self.csv_data = get_param_by_id_name('csv')

    def test_count(self):
        # sort by value.
        # Use out.to_csv() instead of str(out) to ensure rows are output in index order (otherwise variable)
        set_string(self.col_pval, 'Date')

        out = execute_wfmodule(self.wf_module)
        self.assertEqual(out.to_csv(index=False), 'date,count\n2011-01-10,5\n2011-01-15,1\n2016-07-25,1\n')

        # sort by date & set groupby to 'seconds'
        set_integer(self.group_pval, 0)  # 0 = group by seconds
        out = execute_wfmodule(self.wf_module)
        self.assertEqual(out.to_csv(index=False),
                         'date,count\n2011-01-10 00:00:00,1\n2011-01-10 00:00:01,2\n2011-01-10 00:01:00,1\n2011-01-10 01:00:00,1\n2011-01-15 00:00:00,1\n2016-07-25 00:00:00,1\n')

        # sort by date & set groupby to 'minutes'
        set_integer(self.group_pval, 1)  # 0 = group by minutes
        out = execute_wfmodule(self.wf_module)
        self.assertEqual(out.to_csv(index=False),
                         'date,count\n2011-01-10 00:00,3\n2011-01-10 00:01,1\n2011-01-10 01:00,1\n2011-01-15 00:00,1\n2016-07-25 00:00,1\n')

        # sort by date & set groupby to 'hours'
        set_integer(self.group_pval, 2)  # 0 = group by minutes
        out = execute_wfmodule(self.wf_module)
        self.assertEqual(out.to_csv(index=False),
                         'date,count\n2011-01-10 00:00,4\n2011-01-10 01:00,1\n2011-01-15 00:00,1\n2016-07-25 00:00,1\n')

        # sort by date & set groupby to 'months'
        set_integer(self.group_pval, 4)  # 4 = group by months
        out = execute_wfmodule(self.wf_module)
        self.assertEqual(out.to_csv(index=False), 'date,count\n2011-01,6\n2016-07,1\n')

        # sort by date & set groupby to 'quarters'
        set_integer(self.group_pval, 5)  # 4 = group by quarters
        out = execute_wfmodule(self.wf_module)
        self.assertEqual(out.to_csv(index=False), 'date,count\n2011 Q1,6\n2016 Q3,1\n')

        # sort by date & set groupby to 'years'
        set_integer(self.group_pval, 6)  # 6 = group by years
        out = execute_wfmodule(self.wf_module)
        self.assertEqual(out.to_csv(index=False), 'date,count\n2011,6\n2016,1\n')

    def test_bad_colname(self):
        # NOP if no column given
        set_string(self.col_pval, '')
        out = execute_wfmodule(self.wf_module)
        self.wf_module.refresh_from_db()
        self.assertEqual(self.wf_module.status, WfModule.READY)
        self.assertFalse(out.empty)

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

    def test_time_only(self):
        set_string(self.csv_data, self.count_csv_time)
        set_string(self.col_pval, 'Date')

        execute_wfmodule(self.wf_module)
        self.wf_module.refresh_from_db()
        self.assertEqual(self.wf_module.status, 'error')
        self.assertEqual(self.wf_module.error_msg, 'Column Date only contains time values. Group by Hour, Minute or Second.')

        # Set to hours
        set_integer(self.group_pval, 2)
        out = execute_wfmodule(self.wf_module)
        self.wf_module.refresh_from_db()
        self.assertEqual(out.to_csv(index=False), 'date,count\n00:00,3\n01:00,1\n11:00,2\n12:00,1\n')

    def test_date_only(self):
        set_string(self.csv_data, self.count_csv_dates)
        set_string(self.col_pval, 'Date')
        set_integer(self.group_pval, 2)

        execute_wfmodule(self.wf_module)
        self.wf_module.refresh_from_db()
        self.assertEqual(self.wf_module.status, 'error')
        self.assertEqual(self.wf_module.error_msg, 'Column Date only contains date values. Group by Day, Month, Quarter or Year.')

    def test_timestamps(self):
        set_string(self.csv_data, self.count_csv_dates)
        set_string(self.col_pval, 'Date')
        out = execute_wfmodule(self.wf_module)
        self.wf_module.refresh_from_db()
        self.assertEqual(out.to_csv(index=False), 'date,count\n2011-01-10,5\n2011-01-15,1\n2016-07-25,1\n')
