import io
import pandas
import numpy as np
from server.tests.utils import LoggedInTestCase, create_testdata_workflow, \
        load_and_add_module, get_param_by_id_name, set_string, set_integer
from server.execute import execute_nocache
from server.modules.types import ProcessResult

# test data designed to give different output if sorted by freq vs value
count_csv = '\n'.join([
    'Date,Amount,Foo',
    'Jan 10 2011,10,Foo',
    'Jul 25 2016,5,Goo',
    '2011-01-10T01:00:00.000,1,Hoo',
    'Jan 10 2011 00:00:01,1,Hoo',
    'Jan 10 2011 00:00:01,1,Hoo',
    'Jan 10 2011 00:01:00,1,Hoo',
    'Jan 15 2011,1,Too'
])

count_time_csv = '\n'.join([
    'Date,Amount,Foo',
    '11:00,10,Foo',
    '12:00,5,Goo',
    '01:00:00,1,Hoo',
    '00:00:01,1,Hoo',
    '00:00:01,1,Hoo',
    '00:01:00,1,Hoo',
    'December 15 2017 11:05,1,Too',
])

count_date_csv = '\n'.join([
    'Date,Amount,Foo',
    'Jan 10 2011,10,Foo',
    'Jul 25 2016,5,Goo',
    'Jan 10 2011,1,Hoo',
    'Jan 10 2011,1,Hoo',
    'Jan 10 2011,1,Hoo',
    'Jan 10 2011,1,Hoo',
    'Jan 15 2011 6:00pm,1,Too',
])

# count_unix_timestamp_csv = '\n'.join([
#     'Date,Amount,Foo',
#     '1294617600,10,Foo',
#     '1469404800,5,Goo',
#     '1294621200,1,Hoo',
#     '1294617601,1,Hoo',
#     '1294617601,1,Hoo',
#     '1294617661,1,Hoo',
#     '1295071201,1,Too',
# ])

class CountValuesTests(LoggedInTestCase):
    def setUp(self):
        super(CountValuesTests, self).setUp()  # log in

        workflow = create_testdata_workflow(count_csv)

        self.wf_module = load_and_add_module('countbydate', workflow=workflow)
        self.col_pval = get_param_by_id_name('column')
        self.group_pval = get_param_by_id_name('groupby')
        self.operation_pval = get_param_by_id_name('operation')
        self.target_pval = get_param_by_id_name('targetcolumn')
        self.csv_data = get_param_by_id_name('csv')

    def _assertRendersTable(self, csv_rows):
        csv = '\n'.join(csv_rows)
        expected_table = pandas.read_csv(io.StringIO(csv), dtype={
            'Date': str,
            'Time': str,
            'count': np.int64
        })
        expected = ProcessResult(expected_table)
        result = execute_nocache(self.wf_module)
        self.assertEqual(result, expected)

    def test_count(self):
        # sort by value.
        set_string(self.col_pval, 'Date')
        self._assertRendersTable([
            'Date,count',
            '2011-01-10,5',
            '2011-01-15,1',
            '2016-07-25,1',
        ])

        # sort by date & set groupby to 'seconds'
        set_integer(self.group_pval, 0)  # 0 = group by seconds
        self._assertRendersTable([
            'Date,count',
            '2011-01-10 00:00:00,1',
            '2011-01-10 00:00:01,2',
            '2011-01-10 00:01:00,1',
            '2011-01-10 01:00:00,1',
            '2011-01-15 00:00:00,1',
            '2016-07-25 00:00:00,1',
        ])

        # sort by date & set groupby to 'minutes'
        set_integer(self.group_pval, 1)  # 0 = group by minutes
        self._assertRendersTable([
            'Date,count',
            '2011-01-10 00:00,3',
            '2011-01-10 00:01,1',
            '2011-01-10 01:00,1',
            '2011-01-15 00:00,1',
            '2016-07-25 00:00,1',
        ])

        # sort by date & set groupby to 'hours'
        set_integer(self.group_pval, 2)  # 0 = group by minutes
        self._assertRendersTable([
            'Date,count',
            '2011-01-10 00:00,4',
            '2011-01-10 01:00,1',
            '2011-01-15 00:00,1',
            '2016-07-25 00:00,1',
        ])

        # sort by date & set groupby to 'months'
        set_integer(self.group_pval, 4)  # 4 = group by months
        self._assertRendersTable([
            'Date,count',
            '2011-01,6',
            '2016-07,1',
        ])

        # sort by date & set groupby to 'quarters'
        set_integer(self.group_pval, 5)  # 4 = group by quarters
        self._assertRendersTable([
            'Date,count',
            '2011 Q1,6',
            '2016 Q3,1',
        ])

        # sort by date & set groupby to 'years'
        set_integer(self.group_pval, 6)  # 6 = group by years
        self._assertRendersTable([
            'Date,count',
            '2011,6',
            '2016,1',
        ])

    def test_bad_colname(self):
        # NOP if no column given
        set_string(self.col_pval, '')
        result = execute_nocache(self.wf_module)
        self.assertEqual(
            result,
            ProcessResult(pandas.read_csv(io.StringIO(count_csv)))
        )

        # bad column name should produce error
        set_string(self.col_pval, 'hilarious')
        result = execute_nocache(self.wf_module)
        self.assertEqual(
            result,
            ProcessResult(error="There is no column named 'hilarious'")
        )

    def test_bad_dates(self):
        # integers are not dates
        set_string(self.col_pval, 'Amount')
        result = execute_nocache(self.wf_module)
        self.assertEqual(
            result,
            ProcessResult(
                error="The column 'Amount' does not appear to be dates or time"
            )
        )

        # Weird strings are not dates (different error code path)
        set_string(self.col_pval, 'Foo')
        result = execute_nocache(self.wf_module)
        self.assertEqual(
            result,
            ProcessResult(
                error="The column 'Foo' does not appear to be dates or time"
            )
        )

    def test_time_only(self):
        set_string(self.csv_data, count_time_csv)
        set_string(self.col_pval, 'Date')

        result = execute_nocache(self.wf_module)
        self.assertEqual(result, ProcessResult(error=(
            "The column 'Date' only contains time values. "
            'Please group by Hour, Minute or Second.'
        )))

        # Set to hours
        set_integer(self.group_pval, 2)
        self._assertRendersTable([
            'Date,count',
            '00:00,3',
            '01:00,1',
            '11:00,2',
            '12:00,1',
        ])

    def test_date_only(self):
        set_string(self.csv_data, count_date_csv)
        set_string(self.col_pval, 'Date')
        set_integer(self.group_pval, 2)

        result = execute_nocache(self.wf_module)
        self.assertEqual(result, ProcessResult(error=(
            "The column 'Date' only contains date values. "
            'Please group by Day, Month, Quarter or Year.'
        )))

        set_integer(self.group_pval, 4)  # 4 = group by months
        self._assertRendersTable([
            'Date,count',
            '2011-01,6',
            '2016-07,1',
        ])

    # def test_unix_timestamps(self):
    #     set_string(self.csv_data, count_unix_timestamp_csv)
    #     set_string(self.col_pval, 'Date')
    #
    #     self._assertRendersTable([
    #         'Date,count',
    #         '2011-01-10,5',
    #         '2011-01-15,1',
    #         '2016-07-25,1',
    #     ])
