import dateutil
import numpy as np
import pandas
from pandas.testing import assert_frame_equal
from django.test import override_settings, SimpleTestCase
from server.modules.countbydate import CountByDate
from server.modules.types import ProcessResult
from .util import MockParams


P = MockParams.factory(column='', groupby=0, operation=0, targetcolumn='',
                       include_missing_dates=False)


def render(table, params):
    return ProcessResult.coerce(CountByDate.render(table, params))


def dt(s):
    return dateutil.parser.parse(s)


# test data designed to give different output if sorted by freq vs value
count_table = pandas.DataFrame({
    'Date': [dt('2011-01-10T00:00:00.000Z'), dt('2016-07-25T00:00:00.000Z'),
             dt('2011-01-10T00:00:01.321Z'), dt('2011-01-10T00:00:01.123Z'),
             dt('2011-01-10T00:01:00.000Z'), dt('2011-01-10T01:00:00.001Z'),
             dt('2011-01-15T00:00:00.000Z')],
    'Amount': [10, 5, 1, 1, 1, 1, 1],
})

# aggregating rules are a bit different.
# 2018-01-01: single value
# 2018-01-02: nothing
# 2018-01-03: several values
# 2018-01-04: one NA
# 2018-01-05: one value, one NA
agg_table = pandas.DataFrame({
    'Date': [dt('2018-01-01'), dt('2018-01-03'), dt('2018-01-03'),
             dt('2018-01-03'), dt('2018-01-04'), dt('2018-01-05'),
             dt('2018-01-05')],
    'Amount': [8, 5, 1, 3, np.nan, 2, np.nan],
})

# aggregating with integers (no NaN) can be different
# 2018-01-01: single value
# 2018-01-02: nothing
# 2018-01-03: several values
# 2018-01-04: nothing
# 2018-01-05: single value
agg_int_table = pandas.DataFrame({
    'Date': [dt('2018-01-01'), dt('2018-01-03'), dt('2018-01-03'),
             dt('2018-01-03'), dt('2018-01-05')],
    'Amount': [8, 5, 1, 3, 2],
})


class CountByDateTests(SimpleTestCase):
    def _assertRendersTable(self, in_table, params, expected_table):
        result = render(in_table, params)

        if hasattr(expected_table['Date'], 'dt'):
            expected_table['Date'] = \
                expected_table['Date'].dt.tz_localize(None)

        self.assertEqual(result.error, '')
        self.assertEqual(result.quick_fixes, [])
        assert_frame_equal(result.dataframe, expected_table)

    def assertResultEqual(self, result, expected):
        self.assertEqual(result.error, expected.error)
        assert_frame_equal(result.dataframe, expected.dataframe)

    def test_count_by_date(self):
        self._assertRendersTable(
            count_table,
            P(column='Date', groupby=3),  # 3 = group by days
            pandas.DataFrame({
                'Date': [dt('2011-01-10'), dt('2011-01-15'), dt('2016-07-25')],
                'count': [5, 1, 1],
            })
        )

    def test_count_by_seconds(self):
        self._assertRendersTable(
            count_table,
            P(column='Date', groupby=0),  # 0 = group by second
            pandas.DataFrame({
                'Date': [
                    dt('2011-01-10T00:00:00Z'),
                    dt('2011-01-10T00:00:01Z'),
                    dt('2011-01-10T00:01:00Z'),
                    dt('2011-01-10T01:00:00Z'),
                    dt('2011-01-15T00:00:00Z'),
                    dt('2016-07-25T00:00:00Z'),
                ],
                'count': [1, 2, 1, 1, 1, 1],
            })
        )

    def test_count_by_minutes(self):
        self._assertRendersTable(
            count_table,
            P(column='Date', groupby=1),  # 1 = group by minute
            pandas.DataFrame({
                'Date': [dt('2011-01-10T00:00Z'), dt('2011-01-10T00:01Z'),
                         dt('2011-01-10T01:00Z'), dt('2011-01-15T00:00Z'),
                         dt('2016-07-25T00:00Z')],
                'count': [3, 1, 1, 1, 1],
            })
        )

    def test_count_by_hours(self):
        self._assertRendersTable(
            count_table,
            P(column='Date', groupby=2),  # 2 = group by hour
            pandas.DataFrame({
                'Date': [dt('2011-01-10T00:00Z'), dt('2011-01-10T01:00Z'),
                         dt('2011-01-15T00:00Z'), dt('2016-07-25T00:00Z')],
                'count': [4, 1, 1, 1],
            })
        )

    def test_count_by_months(self):
        self._assertRendersTable(
            count_table,
            P(column='Date', groupby=4),  # 4 = group by month
            pandas.DataFrame({
                'Date': [dt('2011-01-01'), dt('2016-07-01')],
                'count': [6, 1],
            })
        )

    def test_count_by_quarters(self):
        self._assertRendersTable(
            count_table,
            P(column='Date', groupby=5),  # 5 = group by quarter
            pandas.DataFrame({
                'Date': ['2011 Q1', '2016 Q3'],
                'count': [6, 1]
            })
        )

    def test_count_by_years(self):
        self._assertRendersTable(
            count_table,
            P(column='Date', groupby=6),  # 6 = group by year
            pandas.DataFrame({
                'Date': [dt('2011-01-01'), dt('2016-01-01')],
                'count': [6, 1],
            })
        )

    def test_count_by_second_of_day(self):
        self._assertRendersTable(
            count_table,
            P(column='Date', groupby=7),  # 7 = second of day
            pandas.DataFrame({
                'Date': ['00:00:00', '00:00:01', '00:01:00', '01:00:00'],
                'count': [3, 2, 1, 1],
            })
        )

    def test_count_by_minute_of_day(self):
        self._assertRendersTable(
            count_table,
            P(column='Date', groupby=8),  # 8 = minute of day
            pandas.DataFrame({
                'Date': ['00:00', '00:01', '01:00'],
                'count': [5, 1, 1],
            })
        )

    def test_count_by_hour_of_day(self):
        self._assertRendersTable(
            count_table,
            P(column='Date', groupby=9),  # 9 = hour of day
            pandas.DataFrame({
                'Date': ['00:00', '01:00'],
                'count': [6, 1],
            })
        )

    def test_no_col_gives_noop(self):
        result = render(count_table, P(column=''))
        expected = ProcessResult(count_table)
        self.assertResultEqual(result, expected)

    def test_invalid_colname_gives_error(self):
        # bad column name should produce error
        result = render(count_table, P(column='hilarious'))
        self.assertEqual(result.error, 'There is no column named "hilarious"')

    def test_integer_dates_give_error(self):
        # integers are not dates
        table = pandas.DataFrame({'A': [1], 'B': [2]})
        result = render(table, P(column='A'))
        self.assertEqual(result.error, 'Column "A" must be Date & Time')

    def test_string_dates_give_error(self):
        # integers are not dates
        table = pandas.DataFrame({'A': ['2018'], 'B': [2]})
        result = render(table, P(column='A'))
        self.assertEqual(result.error, 'Column "A" must be Date & Time')
        self.assertEqual(len(result.quick_fixes), 1)

    def test_average_no_error_when_missing_target(self):
        # 1 = mean
        params = P(column='Date', operation=1, targetcolumn='')
        result = render(count_table, params)
        self.assertResultEqual(
            result,
            ProcessResult(count_table)
        )

    def test_average_require_target(self):
        params = P(column='Date', operation=1, targetcolumn='Invalid')
        result = render(count_table, params)
        self.assertEqual(result.error, 'There is no column named "Invalid"')

    def test_average_by_date(self):
        self._assertRendersTable(
            agg_table,
            P(column='Date', groupby=3, operation=1, targetcolumn='Amount'),
            pandas.DataFrame({
                # NaN for 2018-01-04 omitted; NaN for 2018-01-05 omitted
                'Date': [dt('2018-01-01'), dt('2018-01-03'), dt('2018-01-05')],
                'Amount': [8.0, 3.0, 2.0],
            })
        )

    def test_sum_by_date(self):
        # 2 = sum
        self._assertRendersTable(
            agg_table,
            P(column='Date', groupby=3, operation=2, targetcolumn='Amount'),
            pandas.DataFrame({
                # NaN for 2018-01-04 omitted; NaN for 2018-01-05 omitted
                'Date': [dt('2018-01-01'), dt('2018-01-03'), dt('2018-01-05')],
                'Amount': [8.0, 9.0, 2.0],
            })
        )

    def test_min_by_date(self):
        self._assertRendersTable(
            agg_table,
            # 3 = min
            P(column='Date', groupby=3, operation=3, targetcolumn='Amount'),
            pandas.DataFrame({
                # NaN for 2018-01-04 omitted; NaN for 2018-01-05 omitted
                'Date': [dt('2018-01-01'), dt('2018-01-03'), dt('2018-01-05')],
                'Amount': [8.0, 1.0, 2.0],
            })
        )

    def test_max_by_date(self):
        self._assertRendersTable(
            agg_table,
            # 4 = max
            P(column='Date', groupby=3, operation=4, targetcolumn='Amount'),
            pandas.DataFrame({
                # NaN for 2018-01-04 omitted; NaN for 2018-01-05 omitted
                'Date': [dt('2018-01-01'), dt('2018-01-03'), dt('2018-01-05')],
                'Amount': [8.0, 5.0, 2.0],
            })
        )

    def test_include_missing_dates_with_count(self):
        self._assertRendersTable(
            agg_table,
            # 0 = count
            P(column='Date', include_missing_dates=True, groupby=3,
              operation=0),
            # Output should be integers
            pandas.DataFrame({
                'Date': [dt('2018-01-01'), dt('2018-01-02'), dt('2018-01-03'),
                         dt('2018-01-04'), dt('2018-01-05')],
                'count': [1, 0, 3, 1, 2]
            })
        )

    def test_include_missing_dates_with_int_sum(self):
        self._assertRendersTable(
            agg_int_table,
            # 2 = sum
            P(column='Date', include_missing_dates=True, groupby=3,
              operation=2, targetcolumn='Amount'),
            # Output should be integers
            pandas.DataFrame({
                'Date': [dt('2018-01-01'), dt('2018-01-02'), dt('2018-01-03'),
                         dt('2018-01-04'), dt('2018-01-05')],
                'Amount': [8, 0, 9, 0, 2],
            })
        )

    def test_include_missing_dates_with_1_date(self):
        self._assertRendersTable(
            pandas.DataFrame({'Date': [dt('2018-01-01'), dt('2018-01-01')]}),
            P(column='Date', include_missing_dates=True, groupby=3),
            pandas.DataFrame({'Date': [dt('2018-01-01')], 'count': [2]})
        )

    def test_include_missing_dates_with_0_date(self):
        self._assertRendersTable(
            pandas.DataFrame({'Date': [pandas.NaT, pandas.NaT]}),
            P(column='Date', include_missing_dates=True, groupby=3),
            pandas.DataFrame({'Date': pandas.DatetimeIndex([]),
                              'count': pandas.Int64Index([])})
        )

    def test_include_missing_dates_with_float_sum(self):
        self._assertRendersTable(
            agg_table,
            # 2 = sum
            P(column='Date', include_missing_dates=True, groupby=3,
              operation=2, targetcolumn='Amount'),
            # Output should be integers
            pandas.DataFrame({
                'Date': [dt('2018-01-01'), dt('2018-01-02'), dt('2018-01-03'),
                         dt('2018-01-04'), dt('2018-01-05')],
                'Amount': [8.0, 0.0, 9.0, 0.0, 2.0],
            })
        )

    def test_include_missing_dates_with_float_min(self):
        self._assertRendersTable(
            agg_table,
            # 3 = min
            P(column='Date', include_missing_dates=True, groupby=3,
              operation=3, targetcolumn='Amount'),
            # Output should be integers
            pandas.DataFrame({
                'Date': [dt('2018-01-01'), dt('2018-01-02'), dt('2018-01-03'),
                         dt('2018-01-04'), dt('2018-01-05')],
                'Amount': [8.0, np.nan, 1.0, np.nan, 2.0],
            })
        )

    def test_include_missing_dates_with_int_min(self):
        # Same as float_min: missing values are NaN
        self._assertRendersTable(
            agg_int_table,
            # 3 = min
            P(column='Date', include_missing_dates=True, groupby=3,
              operation=3, targetcolumn='Amount'),
            # Output should be integers
            pandas.DataFrame({
                'Date': [dt('2018-01-01'), dt('2018-01-02'), dt('2018-01-03'),
                         dt('2018-01-04'), dt('2018-01-05')],
                'Amount': [8.0, np.nan, 1.0, np.nan, 2.0],
            })
        )

    def test_nix_missing_dates(self):
        # https://www.pivotaltracker.com/story/show/160632877
        self._assertRendersTable(
            pandas.DataFrame({
                'Date': [dt('2018-01-01'), None, dt('2018-01-02')],
                'Amount': [np.nan, 2, 3],
            }),
            P(column='Date', groupby=3, operation=3, targetcolumn='Amount'),
            pandas.DataFrame({'Date': [dt('2018-01-02')], 'Amount': 3.0})
        )

    @override_settings(MAX_ROWS_PER_TABLE=100)
    def test_include_too_many_missing_dates(self):
        # 0 - group by seconds
        params = P(column='Date', groupby=0, include_missing_dates=True)
        result = render(count_table, params)
        self.assertEqual(
            result.error,
            ('Including missing dates would create 174787201 rows, '
             'but the maximum allowed is 100')
        )
