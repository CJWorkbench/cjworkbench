import datetime
from typing import Literal, NamedTuple, Optional

import pandas as pd
from pandas.testing import assert_series_equal

from linechart import XSeries


class Column(NamedTuple):
    type: Literal["timestamp", "number", "text"]
    format: Optional[str] = None


def test_json_compatible_values_timestamp():
    assert_series_equal(
        XSeries(
            pd.Series(
                ["2020-11-30", "2020-12-07", "2020-12-14", "2020-12-21", "2020-12-28"],
                dtype="datetime64[ns]",
            ),
            Column("timestamp"),
        ).json_compatible_values,
        pd.Series(
            [
                "2020-11-30T00:00:00Z",
                "2020-12-07T00:00:00Z",
                "2020-12-14T00:00:00Z",
                "2020-12-21T00:00:00Z",
                "2020-12-28T00:00:00Z",
            ]
        ),
    )


def test_json_compatible_values_date():
    assert_series_equal(
        XSeries(
            pd.Series(
                ["2020-11-30", "2020-12-07", "2020-12-14", "2020-12-21", "2020-12-28"],
                dtype="period[D]",
            ),
            Column("date", "week"),
        ).json_compatible_values,
        pd.Series(
            [
                "2020-11-30",
                "2020-12-07",
                "2020-12-14",
                "2020-12-21",
                "2020-12-28",
            ]
        ),
    )


def test_timestamp_ticks_weeks():
    x_series = XSeries(
        pd.Series(
            ["2020-11-30", "2020-12-07", "2020-12-14", "2020-12-21", "2020-12-28"],
            dtype="datetime64[ns]",
        ),
        Column("timestamp"),
    )
    assert x_series.timestamp_tick_values_and_format == (
        [
            datetime.date(2020, 11, 30),
            datetime.date(2020, 12, 7),
            datetime.date(2020, 12, 14),
            datetime.date(2020, 12, 21),
            datetime.date(2020, 12, 28),
        ],
        "%b %-d, %Y",
    )


def test_timestamp_ticks_impute_weeks():
    x_series = XSeries(
        pd.Series(
            ["2020-11-30", "2020-12-14", "2020-12-28"],
            dtype="datetime64[ns]",
        ),
        Column("timestamp"),
    )
    assert x_series.timestamp_tick_values_and_format == (
        [
            datetime.date(2020, 11, 30),
            datetime.date(2020, 12, 7),
            datetime.date(2020, 12, 14),
            datetime.date(2020, 12, 21),
            datetime.date(2020, 12, 28),
        ],
        "%b %-d, %Y",
    )


def test_timestamp_ticks_reduce_weeks_by_2():
    x_series = XSeries(
        pd.Series(
            [
                "2020-10-05",
                "2020-10-12",
                "2020-10-19",
                "2020-10-26",
                "2020-11-02",
                "2020-11-09",
                "2020-11-16",
                "2020-11-23",
                "2020-11-30",
                "2020-12-07",
                "2020-12-14",
                "2020-12-21",
                "2020-12-28",
            ],
            dtype="datetime64[ns]",
        ),
        Column("timestamp"),
    )
    assert x_series.timestamp_tick_values_and_format == (
        [
            datetime.date(2020, 10, 5),
            datetime.date(2020, 10, 19),
            datetime.date(2020, 11, 2),
            datetime.date(2020, 11, 16),
            datetime.date(2020, 11, 30),
            datetime.date(2020, 12, 14),
            datetime.date(2020, 12, 28),
        ],
        "%b %-d, %Y",
    )


def test_timestamp_ticks_reduce_weeks_by_2_and_impute_start_week():
    x_series = XSeries(
        pd.Series(
            [
                "2020-10-12",
                "2020-10-19",
                "2020-10-26",
                "2020-11-02",
                "2020-11-09",
                "2020-11-16",
                "2020-11-23",
                "2020-11-30",
                "2020-12-07",
                "2020-12-14",
                "2020-12-21",
                "2020-12-28",
            ],
            dtype="datetime64[ns]",
        ),
        Column("timestamp"),
    )
    assert x_series.timestamp_tick_values_and_format[0][0] == datetime.date(2020, 10, 5)


def test_timestamp_ticks_months():
    x_series = XSeries(
        pd.Series(
            [
                "2020-01-01",
                "2020-02-01",
                "2020-03-01",
                "2020-04-01",
                "2020-05-01",
                "2020-06-01",
                "2020-07-01",
                "2020-08-01",
                "2020-09-01",
                "2020-10-01",
                "2020-11-01",
                "2020-12-01",
            ],
            dtype="datetime64[ns]",
        ),
        Column("timestamp"),
    )
    assert x_series.timestamp_tick_values_and_format == (
        [
            datetime.date(2019, 12, 1),
            datetime.date(2020, 2, 1),
            datetime.date(2020, 4, 1),
            datetime.date(2020, 6, 1),
            datetime.date(2020, 8, 1),
            datetime.date(2020, 10, 1),
            datetime.date(2020, 12, 1),
        ],
        "%b %Y",
    )


def test_timestamp_ticks_years():
    x_series = XSeries(
        pd.Series(
            ["1960", "1970", "1980", "1990", "2011", "2021"],
            dtype="datetime64[ns]",
        ),
        Column("timestamp"),
    )
    assert x_series.timestamp_tick_values_and_format == (
        [
            datetime.date(1958, 1, 1),
            datetime.date(1967, 1, 1),
            datetime.date(1976, 1, 1),
            datetime.date(1985, 1, 1),
            datetime.date(1994, 1, 1),
            datetime.date(2003, 1, 1),
            datetime.date(2012, 1, 1),
            datetime.date(2021, 1, 1),
        ],
        "%Y",
    )
