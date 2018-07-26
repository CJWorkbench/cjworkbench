import io
import pandas
import numpy as np
from django.test import override_settings
from server.tests.utils import LoggedInTestCase, create_testdata_workflow, \
        load_and_add_module, get_param_by_id_name, set_param
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

# aggregating rules are a bit different.
# 2018-01-01: single value
# 2018-01-02: nothing
# 2018-01-03: several values
# 2018-01-04: one NA
# 2018-01-05: one value, one NA
agg_csv = '\n'.join([
    'Date,Amount',
    '2018-01-01,8',
    '2018-01-03,5',
    '2018-01-03,1',
    '2018-01-03,3',
    '2018-01-04,NaN',
    '2018-01-05,2',
    '2018-01-05,NaN',
])

# aggregating with integers (no NaN) can be different
# 2018-01-01: single value
# 2018-01-02: nothing
# 2018-01-03: several values
agg_int_csv = '\n'.join([
    'Date,Amount',
    '2018-01-01,8',
    '2018-01-03,5',
    '2018-01-03,1',
    '2018-01-03,3',
    '2018-01-05,2',
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
        self.include_missing_dates_pval = \
            get_param_by_id_name('include_missing_dates')
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

    def test_count_by_date(self):
        set_param(self.col_pval, 'Date')
        self._assertRendersTable([
            'Date,count',
            '2011-01-10,5',
            '2011-01-15,1',
            '2016-07-25,1',
        ])

    def test_count_by_seconds(self):
        set_param(self.col_pval, 'Date')
        set_param(self.group_pval, 0)  # 0 = group by seconds
        self._assertRendersTable([
            'Date,count',
            '2011-01-10T00:00:00,1',
            '2011-01-10T00:00:01,2',
            '2011-01-10T00:01:00,1',
            '2011-01-10T01:00:00,1',
            '2011-01-15T00:00:00,1',
            '2016-07-25T00:00:00,1',
        ])

    def test_count_by_minutes(self):
        set_param(self.col_pval, 'Date')
        set_param(self.group_pval, 1)  # 1 = group by minutes
        self._assertRendersTable([
            'Date,count',
            '2011-01-10T00:00,3',
            '2011-01-10T00:01,1',
            '2011-01-10T01:00,1',
            '2011-01-15T00:00,1',
            '2016-07-25T00:00,1',
        ])

    def test_count_by_hours(self):
        set_param(self.col_pval, 'Date')
        set_param(self.group_pval, 2)  # 2 = group by hours
        self._assertRendersTable([
            'Date,count',
            '2011-01-10T00:00,4',
            '2011-01-10T01:00,1',
            '2011-01-15T00:00,1',
            '2016-07-25T00:00,1',
        ])

    def test_count_by_months(self):
        set_param(self.col_pval, 'Date')
        set_param(self.group_pval, 4)  # 4 = group by months
        self._assertRendersTable([
            'Date,count',
            '2011-01,6',
            '2016-07,1',
        ])

    def test_count_by_quarters(self):
        set_param(self.col_pval, 'Date')
        set_param(self.group_pval, 5)  # 5 = group by quarters
        self._assertRendersTable([
            'Date,count',
            '2011 Q1,6',
            '2016 Q3,1',
        ])

    def test_count_by_years(self):
        set_param(self.col_pval, 'Date')
        set_param(self.group_pval, 6)  # 6 = group by years
        self._assertRendersTable([
            'Date,count',
            '2011,6',
            '2016,1',
        ])

    def test_no_col_gives_noop(self):
        set_param(self.col_pval, '')
        result = execute_nocache(self.wf_module)
        self.assertEqual(
            result,
            ProcessResult(pandas.read_csv(io.StringIO(count_csv)))
        )

    def test_invalid_colname_gives_error(self):
        # bad column name should produce error
        set_param(self.col_pval, 'hilarious')
        result = execute_nocache(self.wf_module)
        self.assertEqual(
            result,
            ProcessResult(error="There is no column named 'hilarious'")
        )

    def test_integer_dates_give_error(self):
        # integers are not dates
        set_param(self.col_pval, 'Amount')
        result = execute_nocache(self.wf_module)
        self.assertEqual(
            result,
            ProcessResult(
                error="The column 'Amount' does not appear to be dates or times"
            )
        )

    def test_weird_strings_give_error(self):
        # Weird strings are not dates (different error code path)
        set_param(self.col_pval, 'Foo')
        result = execute_nocache(self.wf_module)
        self.assertEqual(
            result,
            ProcessResult(
                error="The column 'Foo' does not appear to be dates or times"
            )
        )

    def test_time_only_refuse_date_period(self):
        set_param(self.csv_data, count_time_csv)
        set_param(self.col_pval, 'Date')
        set_param(self.group_pval, 5)
        result = execute_nocache(self.wf_module)
        self.assertEqual(result, ProcessResult(error=(
            "The column 'Date' only contains time values. "
            'Please group by Second, Minute or Hour.'
        )))

    def test_time_only_format_hours(self):
        set_param(self.csv_data, count_time_csv)
        set_param(self.col_pval, 'Date')
        set_param(self.group_pval, 2)
        self._assertRendersTable([
            'Date,count',
            '00:00,3',
            '01:00,1',
            '11:00,2',
            '12:00,1',
        ])

    def test_date_only_refuse_time_period(self):
        set_param(self.csv_data, count_date_csv)
        set_param(self.col_pval, 'Date')
        set_param(self.group_pval, 2)

        result = execute_nocache(self.wf_module)
        self.assertEqual(result, ProcessResult(error=(
            "The column 'Date' only contains date values. "
            'Please group by Day, Month, Quarter or Year.'
        )))

    def test_date_only(self):
        set_param(self.csv_data, count_date_csv)
        set_param(self.col_pval, 'Date')
        set_param(self.group_pval, 4)  # 4 = group by months
        self._assertRendersTable([
            'Date,count',
            '2011-01,6',
            '2016-07,1',
        ])

    def test_average_no_error_when_missing_target(self):
        set_param(self.col_pval, 'Date')
        set_param(self.operation_pval, 1)  # 1 = mean
        set_param(self.target_pval, '')
        result = execute_nocache(self.wf_module)
        self.assertEqual(
            result,
            ProcessResult(pandas.read_csv(io.StringIO(count_csv)))
        )

    def test_average_require_target(self):
        set_param(self.col_pval, 'Date')
        set_param(self.operation_pval, 1)  # 1 = mean
        set_param(self.target_pval, 'Invalid')
        result = execute_nocache(self.wf_module)
        self.assertEqual(result, ProcessResult(error=(
            "There is no column named 'Invalid'"
        )))

    def test_average_by_date(self):
        set_param(self.csv_data, agg_csv)
        set_param(self.col_pval, 'Date')
        set_param(self.operation_pval, 1)  # 1 = mean
        set_param(self.target_pval, 'Amount')
        self._assertRendersTable([
            'Date,Amount',
            '2018-01-01,8.0',
            '2018-01-03,3.0',
            # NaN for 2018-01-04 omitted
            '2018-01-05,2.0',  # NaN omitted
        ])

    def test_sum_by_date(self):
        set_param(self.csv_data, agg_csv)
        set_param(self.col_pval, 'Date')
        set_param(self.operation_pval, 2)  # 2 = sum
        set_param(self.target_pval, 'Amount')
        result = execute_nocache(self.wf_module)
        self.assertEqual(result, ProcessResult(pandas.DataFrame(
            columns=['Date', 'Amount'],
            data=[
                ('2018-01-01', 8.0),
                ('2018-01-03', 9.0),
                # 2018-01-04 is omitted because it's NaN
                ('2018-01-05', 2.0),  # NaN omitted
            ]
        )))

    def test_min_by_date(self):
        set_param(self.csv_data, agg_csv)
        set_param(self.col_pval, 'Date')
        set_param(self.operation_pval, 3)  # 3 = min
        set_param(self.target_pval, 'Amount')
        self._assertRendersTable([
            'Date,Amount',
            '2018-01-01,8.0',
            '2018-01-03,1.0',
            # NaN for 2018-01-04 omitted
            '2018-01-05,2.0',  # NaN omitted
        ])

    def test_max_by_date(self):
        set_param(self.csv_data, agg_csv)
        set_param(self.col_pval, 'Date')
        set_param(self.operation_pval, 4)  # 4 = sum
        set_param(self.target_pval, 'Amount')
        self._assertRendersTable([
            'Date,Amount',
            '2018-01-01,8.0',
            '2018-01-03,5.0',
            # NaN for 2018-01-04 omitted
            '2018-01-05,2.0',  # NaN omitted
        ])

    def test_include_missing_dates_with_count(self):
        set_param(self.csv_data, agg_csv)
        set_param(self.col_pval, 'Date')
        set_param(self.include_missing_dates_pval, True)
        set_param(self.operation_pval, 0)  # 0 = count
        set_param(self.target_pval, 'Amount')
        result = execute_nocache(self.wf_module)
        # Output should be integers
        self.assertEqual(result, ProcessResult(pandas.DataFrame(
            columns=['Date', 'count'],
            data=[
                ('2018-01-01', 1),
                ('2018-01-02', 0),
                ('2018-01-03', 3),
                ('2018-01-04', 1),  # count row with NA
                ('2018-01-05', 2),  # count row with NA
            ]
        )))

    def test_include_missing_dates_with_int_sum(self):
        set_param(self.csv_data, agg_int_csv)
        set_param(self.col_pval, 'Date')
        set_param(self.include_missing_dates_pval, True)
        set_param(self.operation_pval, 2)  # 2 = sum
        set_param(self.target_pval, 'Amount')
        result = execute_nocache(self.wf_module)
        # Output should be integers
        self.assertEqual(result, ProcessResult(pandas.DataFrame(
            columns=['Date', 'Amount'],
            data=[
                ('2018-01-01', 8),
                ('2018-01-02', 0),
                ('2018-01-03', 9),
                ('2018-01-04', 0),
                ('2018-01-05', 2),
            ]
        )))

    def test_include_missing_dates_with_float_sum(self):
        set_param(self.csv_data, agg_csv.replace(',8\n', ',8.1\n'))
        set_param(self.col_pval, 'Date')
        set_param(self.operation_pval, 2)  # 2 = sum
        set_param(self.include_missing_dates_pval, True)
        set_param(self.target_pval, 'Amount')
        result = execute_nocache(self.wf_module)
        # Output should include 0 for missing values
        self.assertEqual(result, ProcessResult(pandas.DataFrame(
            columns=['Date', 'Amount'],
            data=[
                ('2018-01-01', 8.1),
                ('2018-01-02', 0.0),
                ('2018-01-03', 9.0),
                ('2018-01-04', 0.0),
                ('2018-01-05', 2.0),
            ]
        )))

    def test_include_missing_dates_with_float_min(self):
        set_param(self.csv_data, agg_csv.replace(',8\n', ',8.1\n'))
        set_param(self.col_pval, 'Date')
        set_param(self.operation_pval, 3)  # 3 = min
        set_param(self.include_missing_dates_pval, True)
        set_param(self.target_pval, 'Amount')
        result = execute_nocache(self.wf_module)
        # Max should be NaN for missing values
        self.assertEqual(result, ProcessResult(pandas.DataFrame(
            columns=['Date', 'Amount'],
            data=[
                ('2018-01-01', 8.1),
                ('2018-01-02', np.nan),
                ('2018-01-03', 1.0),
                ('2018-01-04', np.nan),
                ('2018-01-05', 2.0),
            ]
        )))

    def test_include_missing_dates_with_int_min(self):
        set_param(self.csv_data, agg_int_csv)
        set_param(self.col_pval, 'Date')
        set_param(self.operation_pval, 3)  # 3 = min
        set_param(self.include_missing_dates_pval, True)
        set_param(self.target_pval, 'Amount')
        result = execute_nocache(self.wf_module)
        # Max should be NaN for missing values ... meaning it's all floats
        self.assertEqual(result, ProcessResult(pandas.DataFrame(
            columns=['Date', 'Amount'],
            data=[
                ('2018-01-01', 8.0),
                ('2018-01-02', np.nan),
                ('2018-01-03', 1.0),
                ('2018-01-04', np.nan),
                ('2018-01-05', 2.0),
            ]
        )))

    @override_settings(MAX_ROWS_PER_TABLE=100)
    def test_include_too_many_missing_dates(self):
        set_param(self.csv_data, count_csv)
        set_param(self.col_pval, 'Date')
        set_param(self.group_pval, 0)  # 0 = group by seconds
        set_param(self.include_missing_dates_pval, True)
        result = execute_nocache(self.wf_module)
        self.assertEqual(result, ProcessResult(error=(
            'Including missing dates would create 174787201 rows, '
            'but the maximum allowed is 100'
        )))
