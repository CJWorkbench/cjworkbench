import dateutil
import io
import pandas
from pandas.testing import assert_frame_equal
import numpy as np
from django.test import override_settings, SimpleTestCase
from server.modules.countbydate import CountByDate
from server.modules.types import ProcessResult


def read_csv(s, *args, **kwargs):
    return pandas.read_csv(io.StringIO(s), *args, **kwargs)


def render(wf_module, table):
    return ProcessResult.coerce(CountByDate.render(wf_module, table))


def dt(s):
    return dateutil.parser.parse(s)


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


class MockWfModule:
    def __init__(self, **kwargs):
        self.column = ''
        self.groupby = 0
        self.operation = 0
        self.targetcolumn = ''
        self.include_missing_dates = False
        for k, v in kwargs.items():
            setattr(self, k, v)

    def get_param_column(self, name, *args, **kwargs):
        return getattr(self, name)

    def get_param_menu_idx(self, name, *args, **kwargs):
        return getattr(self, name)

    def get_param_checkbox(self, name, *args, **kwargs):
        return getattr(self, name)


class CountByDateTests(SimpleTestCase):
    def setUp(self):
        super().setUp()

        self.table = read_csv(count_csv)
        self.wf_module = MockWfModule()

    def _assertRendersTable(self, table, wf_module, csv_rows,
                            parse_dates=['Date']):
        csv = '\n'.join(csv_rows)
        expected_table = read_csv(csv, dtype={
            'Date': str,
            'Time': str,
            'count': np.int64
        }, parse_dates=parse_dates)
        expected = ProcessResult(expected_table)
        result = render(wf_module, table)
        self.assertResultEqual(result, expected)

    def assertResultEqual(self, result, expected):
        self.assertEqual(result.error, expected.error)
        assert_frame_equal(result.dataframe, expected.dataframe)

    def test_count_by_date(self):
        self._assertRendersTable(
            read_csv(count_csv),
            MockWfModule(column='Date', groupby=3),  # 3 = group by days
            [
                'Date,count',
                '2011-01-10,5',
                '2011-01-15,1',
                '2016-07-25,1',
            ]
        )

    def test_count_by_seconds(self):
        self._assertRendersTable(
            read_csv(count_csv),
            MockWfModule(column='Date', groupby=0),  # 0 = group by second
            [
                'Date,count',
                '2011-01-10T00:00:00,1',
                '2011-01-10T00:00:01,2',
                '2011-01-10T00:01:00,1',
                '2011-01-10T01:00:00,1',
                '2011-01-15T00:00:00,1',
                '2016-07-25T00:00:00,1',
            ]
        )

    def test_count_by_minutes(self):
        self._assertRendersTable(
            read_csv(count_csv),
            MockWfModule(column='Date', groupby=1),  # 1 = group by minute
            [
                'Date,count',
                '2011-01-10T00:00,3',
                '2011-01-10T00:01,1',
                '2011-01-10T01:00,1',
                '2011-01-15T00:00,1',
                '2016-07-25T00:00,1',
            ]
        )

    def test_count_by_hours(self):
        self._assertRendersTable(
            read_csv(count_csv),
            MockWfModule(column='Date', groupby=2),  # 2 = group by hour
            [
                'Date,count',
                '2011-01-10T00:00,4',
                '2011-01-10T01:00,1',
                '2011-01-15T00:00,1',
                '2016-07-25T00:00,1',
            ]
        )

    def test_count_by_months(self):
        self._assertRendersTable(
            read_csv(count_csv),
            MockWfModule(column='Date', groupby=4),  # 4 = group by month
            [
                'Date,count',
                '2011-01,6',
                '2016-07,1',
            ]
        )

    def test_count_by_quarters(self):
        self._assertRendersTable(
            read_csv(count_csv),
            MockWfModule(column='Date', groupby=5),  # 5 = group by quarter
            [
                'Date,count',
                '2011 Q1,6',
                '2016 Q3,1',
            ],
            parse_dates=[]
        )

    def test_count_by_years(self):
        self._assertRendersTable(
            read_csv(count_csv),
            MockWfModule(column='Date', groupby=6),  # 6 = group by year
            [
                'Date,count',
                '2011,6',
                '2016,1',
            ]
        )

    def test_no_col_gives_noop(self):
        table = read_csv(count_csv)
        wf_module = MockWfModule(column='')
        result = render(wf_module, table)
        expected = ProcessResult(read_csv(count_csv))
        self.assertResultEqual(expected, result)

    def test_invalid_colname_gives_error(self):
        # bad column name should produce error
        table = read_csv(count_csv)
        wf_module = MockWfModule(column='hilarious')
        result = render(wf_module, table)
        expected = ProcessResult(error="There is no column named 'hilarious'")
        self.assertResultEqual(expected, result)

    def test_integer_dates_give_error(self):
        # integers are not dates
        table = read_csv(count_csv)
        wf_module = MockWfModule(column='Amount')
        result = render(wf_module, table)
        expected = ProcessResult(
            error="The column 'Amount' does not appear to be dates or times"
        )
        self.assertResultEqual(expected, result)

    def test_weird_strings_give_error(self):
        # Weird strings are not dates (different error code path)
        table = read_csv(count_csv)
        wf_module = MockWfModule(column='Foo')
        result = render(wf_module, table)
        expected = ProcessResult(
            error="The column 'Foo' does not appear to be dates or times"
        )
        self.assertResultEqual(expected, result)

    def test_time_only_refuse_date_period(self):
        table = read_csv(count_time_csv)
        wf_module = MockWfModule(column='Date', groupby=5)
        result = render(wf_module, table)
        self.assertResultEqual(result, ProcessResult(error=(
            "The column 'Date' only contains time values. "
            'Please group by Second, Minute or Hour.'
        )))

    def test_time_only_format_hours(self):
        self._assertRendersTable(
            read_csv(count_time_csv),
            MockWfModule(column='Date', groupby=2),  # 2 = group by hour
            [
                'Date,count',
                '00:00,3',
                '01:00,1',
                '11:00,2',
                '12:00,1',
            ],
            parse_dates=[]
        )

    def test_date_only_refuse_time_period(self):
        table = read_csv(count_date_csv)
        wf_module = MockWfModule(column='Date', groupby=2)  # 2 = group by hour
        result = render(wf_module, table)
        self.assertResultEqual(result, ProcessResult(error=(
            "The column 'Date' only contains date values. "
            'Please group by Day, Month, Quarter or Year.'
        )))

    def test_date_only(self):
        self._assertRendersTable(
            read_csv(count_date_csv),
            MockWfModule(column='Date', groupby=4),  # 4 = group by month
            [
                'Date,count',
                '2011-01-01,6',
                '2016-07-01,1',
            ]
        )

    def test_average_no_error_when_missing_target(self):
        table = read_csv(count_csv)
        # 1 = mean
        wf_module = MockWfModule(column='Date', operation=1, targetcolumn='')
        result = render(wf_module, table)
        self.assertResultEqual(
            result,
            ProcessResult(read_csv(count_csv))
        )

    def test_average_require_target(self):
        table = read_csv(count_csv)
        wf_module = MockWfModule(column='Date', operation=1,
                                 targetcolumn='Invalid')
        result = render(wf_module, table)
        self.assertResultEqual(result, ProcessResult(error=(
            "There is no column named 'Invalid'"
        )))

    def test_average_by_date(self):
        self._assertRendersTable(
            read_csv(agg_csv),
            MockWfModule(column='Date', groupby=3, operation=1,
                         targetcolumn='Amount'),
            [
                'Date,Amount',
                '2018-01-01,8.0',
                '2018-01-03,3.0',
                # NaN for 2018-01-04 omitted
                '2018-01-05,2.0',  # NaN omitted
            ]
        )

    def test_sum_by_date(self):
        table = read_csv(agg_csv)
        # 2 = sum
        wf_module = MockWfModule(column='Date', groupby=3, operation=2,
                                 targetcolumn='Amount')
        result = render(wf_module, table)
        self.assertResultEqual(result, ProcessResult(pandas.DataFrame(
            columns=['Date', 'Amount'],
            data=[
                (dt('2018-01-01'), 8.0),
                (dt('2018-01-03'), 9.0),
                # 2018-01-04 is omitted because it's NaN
                (dt('2018-01-05'), 2.0),  # NaN omitted
            ]
        )))

    def test_min_by_date(self):
        self._assertRendersTable(
            read_csv(agg_csv),
            # 3 = min
            MockWfModule(column='Date', groupby=3, operation=3,
                         targetcolumn='Amount'),
            [
                'Date,Amount',
                '2018-01-01,8.0',
                '2018-01-03,1.0',
                # NaN for 2018-01-04 omitted
                '2018-01-05,2.0',  # NaN omitted
            ]
        )

    def test_max_by_date(self):
        self._assertRendersTable(
            read_csv(agg_csv),
            # 4 = max
            MockWfModule(column='Date', groupby=3, operation=4,
                         targetcolumn='Amount'),
            [
                'Date,Amount',
                '2018-01-01,8.0',
                '2018-01-03,5.0',
                # NaN for 2018-01-04 omitted
                '2018-01-05,2.0',  # NaN omitted
            ]
        )

    def test_include_missing_dates_with_count(self):
        table = read_csv(agg_csv)
        # 0 = count
        wf_module = MockWfModule(column='Date', include_missing_dates=True,
                                 groupby=3, operation=0, targetcolumn='Amount')
        result = render(wf_module, table)
        # Output should be integers
        self.assertResultEqual(result, ProcessResult(pandas.DataFrame(
            columns=['Date', 'count'],
            data=[
                (dt('2018-01-01'), 1),
                (dt('2018-01-02'), 0),
                (dt('2018-01-03'), 3),
                (dt('2018-01-04'), 1),  # count row with NA
                (dt('2018-01-05'), 2),  # count row with NA
            ]
        )))

    def test_include_missing_dates_with_int_sum(self):
        table = read_csv(agg_int_csv)
        # 2 = sum
        wf_module = MockWfModule(column='Date', include_missing_dates=True,
                                 groupby=3, operation=2, targetcolumn='Amount')
        result = render(wf_module, table)
        # Output should be integers
        self.assertResultEqual(result, ProcessResult(pandas.DataFrame(
            columns=['Date', 'Amount'],
            data=[
                (dt('2018-01-01'), 8),
                (dt('2018-01-02'), 0),
                (dt('2018-01-03'), 9),
                (dt('2018-01-04'), 0),
                (dt('2018-01-05'), 2),
            ]
        )))

    def test_include_missing_dates_with_float_sum(self):
        table = read_csv(agg_csv.replace(',8\n', ',8.1\n'))
        # 2 = sum
        wf_module = MockWfModule(column='Date', include_missing_dates=True,
                                 groupby=3, operation=2, targetcolumn='Amount')
        result = render(wf_module, table)
        # Output should include 0 for missing values
        self.assertResultEqual(result, ProcessResult(pandas.DataFrame(
            columns=['Date', 'Amount'],
            data=[
                (dt('2018-01-01'), 8.1),
                (dt('2018-01-02'), 0.0),
                (dt('2018-01-03'), 9.0),
                (dt('2018-01-04'), 0.0),
                (dt('2018-01-05'), 2.0),
            ]
        )))

    def test_include_missing_dates_with_float_min(self):
        table = read_csv(agg_csv.replace(',8\n', ',8.1\n'))
        # 3 = min
        wf_module = MockWfModule(column='Date', include_missing_dates=True,
                                 groupby=3, operation=3, targetcolumn='Amount')
        result = render(wf_module, table)
        # Max should be NaN for missing values
        self.assertResultEqual(result, ProcessResult(pandas.DataFrame(
            columns=['Date', 'Amount'],
            data=[
                (dt('2018-01-01'), 8.1),
                (dt('2018-01-02'), np.nan),
                (dt('2018-01-03'), 1.0),
                (dt('2018-01-04'), np.nan),
                (dt('2018-01-05'), 2.0),
            ]
        )))

    def test_include_missing_dates_with_int_min(self):
        table = read_csv(agg_int_csv)
        # 3 = min
        wf_module = MockWfModule(column='Date', include_missing_dates=True,
                                 groupby=3, operation=3, targetcolumn='Amount')
        result = render(wf_module, table)
        # Max should be NaN for missing values ... meaning it's all floats
        self.assertResultEqual(result, ProcessResult(pandas.DataFrame(
            columns=['Date', 'Amount'],
            data=[
                (dt('2018-01-01'), 8.0),
                (dt('2018-01-02'), np.nan),
                (dt('2018-01-03'), 1.0),
                (dt('2018-01-04'), np.nan),
                (dt('2018-01-05'), 2.0),
            ]
        )))

    @override_settings(MAX_ROWS_PER_TABLE=100)
    def test_include_too_many_missing_dates(self):
        table = read_csv(count_csv)
        # 0 - group by seconds
        wf_module = MockWfModule(column='Date', groupby=0,
                                 include_missing_dates=True)
        result = render(wf_module, table)
        self.assertResultEqual(result, ProcessResult(error=(
            'Including missing dates would create 174787201 rows, '
            'but the maximum allowed is 100'
        )))
