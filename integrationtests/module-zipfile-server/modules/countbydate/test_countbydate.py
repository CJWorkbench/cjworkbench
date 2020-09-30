import unittest
from typing import NamedTuple

import dateutil
import numpy as np
import pandas
from countbydate import migrate_params, render
from pandas.testing import assert_frame_equal

from cjwmodule.testing.i18n import i18n_message

class Settings(NamedTuple):
    MAX_ROWS_PER_TABLE: int = 1000


def P(
    column="",
    groupby="second",
    operation="size",
    targetcolumn="",
    include_missing_dates=False,
):
    return dict(
        column=column,
        groupby=groupby,
        operation=operation,
        targetcolumn=targetcolumn,
        include_missing_dates=include_missing_dates,
    )


def dt(s):
    return dateutil.parser.parse(s)


# test data designed to give different output if sorted by freq vs value
count_table = pandas.DataFrame(
    {
        "Date": [
            dt("2011-01-10T00:00:00.000Z"),
            dt("2016-07-25T00:00:00.000Z"),
            dt("2011-01-10T00:00:01.321Z"),
            dt("2011-01-10T00:00:01.123Z"),
            dt("2011-01-10T00:01:00.000Z"),
            dt("2011-01-10T01:00:00.001Z"),
            dt("2011-01-15T00:00:00.000Z"),
        ],
        "Amount": [10, 5, 1, 1, 1, 1, 1],
    }
)

# aggregating rules are a bit different.
# 2018-01-01: single value
# 2018-01-02: nothing
# 2018-01-03: several values
# 2018-01-04: one NA
# 2018-01-05: one value, one NA
agg_table = pandas.DataFrame(
    {
        "Date": [
            dt("2018-01-01"),
            dt("2018-01-03"),
            dt("2018-01-03"),
            dt("2018-01-03"),
            dt("2018-01-04"),
            dt("2018-01-05"),
            dt("2018-01-05"),
        ],
        "Amount": [8, 5, 1, 3, np.nan, 2, np.nan],
    }
)

# aggregating with integers (no NaN) can be different
# 2018-01-01: single value
# 2018-01-02: nothing
# 2018-01-03: several values
# 2018-01-04: nothing
# 2018-01-05: single value
agg_int_table = pandas.DataFrame(
    {
        "Date": [
            dt("2018-01-01"),
            dt("2018-01-03"),
            dt("2018-01-03"),
            dt("2018-01-03"),
            dt("2018-01-05"),
        ],
        "Amount": [8, 5, 1, 3, 2],
    }
)


class CountByDateTests(unittest.TestCase):
    def _assertRendersTable(self, in_table, params, expected_table):
        result = render(in_table, params, settings=Settings())

        if hasattr(expected_table["Date"], "dt"):
            # [adamhooper, 2019-04-03] This seems to say: "if we're in unit
            # tests, don't crash the way we crash on production"
            expected_table["Date"] = expected_table["Date"].dt.tz_localize(None)

        assert_frame_equal(result, expected_table)

    def test_count_by_date(self):
        self._assertRendersTable(
            count_table,
            P(column="Date", groupby="day"),
            pandas.DataFrame(
                {
                    "Date": [dt("2011-01-10"), dt("2011-01-15"), dt("2016-07-25")],
                    "count": [5, 1, 1],
                }
            ),
        )

    def test_count_by_seconds(self):
        self._assertRendersTable(
            count_table,
            P(column="Date", groupby="second"),
            pandas.DataFrame(
                {
                    "Date": [
                        dt("2011-01-10T00:00:00Z"),
                        dt("2011-01-10T00:00:01Z"),
                        dt("2011-01-10T00:01:00Z"),
                        dt("2011-01-10T01:00:00Z"),
                        dt("2011-01-15T00:00:00Z"),
                        dt("2016-07-25T00:00:00Z"),
                    ],
                    "count": [1, 2, 1, 1, 1, 1],
                }
            ),
        )

    def test_count_by_minutes(self):
        self._assertRendersTable(
            count_table,
            P(column="Date", groupby="minute"),
            pandas.DataFrame(
                {
                    "Date": [
                        dt("2011-01-10T00:00Z"),
                        dt("2011-01-10T00:01Z"),
                        dt("2011-01-10T01:00Z"),
                        dt("2011-01-15T00:00Z"),
                        dt("2016-07-25T00:00Z"),
                    ],
                    "count": [3, 1, 1, 1, 1],
                }
            ),
        )

    def test_count_by_hours(self):
        self._assertRendersTable(
            count_table,
            P(column="Date", groupby="hour"),
            pandas.DataFrame(
                {
                    "Date": [
                        dt("2011-01-10T00:00Z"),
                        dt("2011-01-10T01:00Z"),
                        dt("2011-01-15T00:00Z"),
                        dt("2016-07-25T00:00Z"),
                    ],
                    "count": [4, 1, 1, 1],
                }
            ),
        )

    def test_count_by_months(self):
        self._assertRendersTable(
            count_table,
            P(column="Date", groupby="month"),
            pandas.DataFrame(
                {"Date": [dt("2011-01-01"), dt("2016-07-01")], "count": [6, 1]}
            ),
        )

    def test_count_by_quarters(self):
        self._assertRendersTable(
            count_table,
            P(column="Date", groupby="quarter"),
            pandas.DataFrame({"Date": ["2011 Q1", "2016 Q3"], "count": [6, 1]}),
        )

    def test_count_by_years(self):
        self._assertRendersTable(
            count_table,
            P(column="Date", groupby="year"),
            pandas.DataFrame(
                {"Date": [dt("2011-01-01"), dt("2016-01-01")], "count": [6, 1]}
            ),
        )

    def test_count_by_second_of_day(self):
        self._assertRendersTable(
            count_table,
            P(column="Date", groupby="second_of_day"),
            pandas.DataFrame(
                {
                    "Date": ["00:00:00", "00:00:01", "00:01:00", "01:00:00"],
                    "count": [3, 2, 1, 1],
                }
            ),
        )

    def test_count_by_minute_of_day(self):
        self._assertRendersTable(
            count_table,
            P(column="Date", groupby="minute_of_day"),
            pandas.DataFrame({"Date": ["00:00", "00:01", "01:00"], "count": [5, 1, 1]}),
        )

    def test_count_by_hour_of_day(self):
        self._assertRendersTable(
            count_table,
            P(column="Date", groupby="hour_of_day"),
            pandas.DataFrame({"Date": ["00:00", "01:00"], "count": [6, 1]}),
        )

    def test_no_col_gives_noop(self):
        result = render(count_table.copy(), P(column=""), settings=Settings())
        assert_frame_equal(result, count_table)

    def test_mean_no_error_when_missing_target(self):
        params = P(column="Date", operation="mean", targetcolumn="")
        result = render(count_table, params, settings=Settings())
        assert_frame_equal(result, count_table)

    def test_mean_by_date(self):
        self._assertRendersTable(
            agg_table,
            P(column="Date", groupby="day", operation="mean", targetcolumn="Amount"),
            pandas.DataFrame(
                {
                    # NaN for 2018-01-04 omitted; NaN for 2018-01-05 omitted
                    "Date": [dt("2018-01-01"), dt("2018-01-03"), dt("2018-01-05")],
                    "Amount": [8.0, 3.0, 2.0],
                }
            ),
        )

    def test_sum_by_date(self):
        self._assertRendersTable(
            agg_table,
            P(column="Date", groupby="day", operation="sum", targetcolumn="Amount"),
            pandas.DataFrame(
                {
                    # NaN for 2018-01-04 omitted; NaN for 2018-01-05 omitted
                    "Date": [dt("2018-01-01"), dt("2018-01-03"), dt("2018-01-05")],
                    "Amount": [8.0, 9.0, 2.0],
                }
            ),
        )

    def test_min_by_date(self):
        self._assertRendersTable(
            agg_table,
            # 3 = min
            P(column="Date", groupby="day", operation="min", targetcolumn="Amount"),
            pandas.DataFrame(
                {
                    # NaN for 2018-01-04 omitted; NaN for 2018-01-05 omitted
                    "Date": [dt("2018-01-01"), dt("2018-01-03"), dt("2018-01-05")],
                    "Amount": [8.0, 1.0, 2.0],
                }
            ),
        )

    def test_max_by_date(self):
        self._assertRendersTable(
            agg_table,
            # 4 = max
            P(column="Date", groupby="day", operation="max", targetcolumn="Amount"),
            pandas.DataFrame(
                {
                    # NaN for 2018-01-04 omitted; NaN for 2018-01-05 omitted
                    "Date": [dt("2018-01-01"), dt("2018-01-03"), dt("2018-01-05")],
                    "Amount": [8.0, 5.0, 2.0],
                }
            ),
        )

    def test_include_missing_dates_with_count(self):
        self._assertRendersTable(
            agg_table,
            # 0 = count
            P(
                column="Date",
                include_missing_dates=True,
                groupby="day",
                operation="size",
            ),
            # Output should be integers
            pandas.DataFrame(
                {
                    "Date": [
                        dt("2018-01-01"),
                        dt("2018-01-02"),
                        dt("2018-01-03"),
                        dt("2018-01-04"),
                        dt("2018-01-05"),
                    ],
                    "count": [1, 0, 3, 1, 2],
                }
            ),
        )

    def test_include_missing_dates_with_int_sum(self):
        self._assertRendersTable(
            agg_int_table,
            P(
                column="Date",
                include_missing_dates=True,
                groupby="day",
                operation="sum",
                targetcolumn="Amount",
            ),
            # Output should be integers
            pandas.DataFrame(
                {
                    "Date": [
                        dt("2018-01-01"),
                        dt("2018-01-02"),
                        dt("2018-01-03"),
                        dt("2018-01-04"),
                        dt("2018-01-05"),
                    ],
                    "Amount": [8, 0, 9, 0, 2],
                }
            ),
        )

    def test_include_missing_dates_with_1_date(self):
        self._assertRendersTable(
            pandas.DataFrame({"Date": [dt("2018-01-01"), dt("2018-01-01")]}),
            P(column="Date", include_missing_dates=True, groupby="day"),
            pandas.DataFrame({"Date": [dt("2018-01-01")], "count": [2]}),
        )

    def test_include_missing_dates_with_0_date(self):
        self._assertRendersTable(
            pandas.DataFrame({"Date": [pandas.NaT, pandas.NaT]}),
            P(column="Date", include_missing_dates=True, groupby="day"),
            pandas.DataFrame(
                {"Date": pandas.DatetimeIndex([]), "count": pandas.Int64Index([])}
            ),
        )

    def test_include_missing_dates_with_float_sum(self):
        self._assertRendersTable(
            agg_table,
            P(
                column="Date",
                include_missing_dates=True,
                groupby="day",
                operation="sum",
                targetcolumn="Amount",
            ),
            # Output should be integers
            pandas.DataFrame(
                {
                    "Date": [
                        dt("2018-01-01"),
                        dt("2018-01-02"),
                        dt("2018-01-03"),
                        dt("2018-01-04"),
                        dt("2018-01-05"),
                    ],
                    "Amount": [8.0, 0.0, 9.0, 0.0, 2.0],
                }
            ),
        )

    def test_include_missing_dates_with_float_min(self):
        self._assertRendersTable(
            agg_table,
            P(
                column="Date",
                include_missing_dates=True,
                groupby="day",
                operation="min",
                targetcolumn="Amount",
            ),
            # Output should be integers
            pandas.DataFrame(
                {
                    "Date": [
                        dt("2018-01-01"),
                        dt("2018-01-02"),
                        dt("2018-01-03"),
                        dt("2018-01-04"),
                        dt("2018-01-05"),
                    ],
                    "Amount": [8.0, np.nan, 1.0, np.nan, 2.0],
                }
            ),
        )

    def test_include_missing_dates_with_int_min(self):
        # Same as float_min: missing values are NaN
        self._assertRendersTable(
            agg_int_table,
            P(
                column="Date",
                include_missing_dates=True,
                groupby="day",
                operation="min",
                targetcolumn="Amount",
            ),
            # Output should be integers
            pandas.DataFrame(
                {
                    "Date": [
                        dt("2018-01-01"),
                        dt("2018-01-02"),
                        dt("2018-01-03"),
                        dt("2018-01-04"),
                        dt("2018-01-05"),
                    ],
                    "Amount": [8.0, np.nan, 1.0, np.nan, 2.0],
                }
            ),
        )

    def test_nix_missing_dates(self):
        # https://www.pivotaltracker.com/story/show/160632877
        self._assertRendersTable(
            pandas.DataFrame(
                {
                    "Date": [dt("2018-01-01"), None, dt("2018-01-02")],
                    "Amount": [np.nan, 2, 3],
                }
            ),
            P(column="Date", groupby="day", operation="min", targetcolumn="Amount"),
            pandas.DataFrame({"Date": [dt("2018-01-02")], "Amount": 3.0}),
        )

    def test_include_too_many_missing_dates(self):
        # 0 - group by seconds
        params = P(column="Date", groupby="second", include_missing_dates=True)
        result = render(count_table, params, settings=Settings(MAX_ROWS_PER_TABLE=100))
        self.assertEqual(
            result,
            i18n_message(
                "error.tooManyRows",
                {
                    'n_rows': 174787201,
                    'max_rows_per_table': 100,
                }
            ),
        )


class MigrateParamsTest(unittest.TestCase):
    def test_v0(self):
        self.assertEqual(
            migrate_params(
                {
                    "column": "OCCUPANCY_DATE",
                    "groupby": 3,
                    "operation": 2,
                    "targetcolumn": "OCCUPANCY",
                    "include_missing_dates": False,
                }
            ),
            {
                "column": "OCCUPANCY_DATE",
                "groupby": "day",
                "operation": "sum",
                "targetcolumn": "OCCUPANCY",
                "include_missing_dates": False,
            },
        )

    def test_v1(self):
        self.assertEqual(
            migrate_params(
                {
                    "column": "OCCUPANCY_DATE",
                    "groupby": "day",
                    "operation": "sum",
                    "targetcolumn": "OCCUPANCY",
                    "include_missing_dates": False,
                }
            ),
            {
                "column": "OCCUPANCY_DATE",
                "groupby": "day",
                "operation": "sum",
                "targetcolumn": "OCCUPANCY",
                "include_missing_dates": False,
            },
        )
