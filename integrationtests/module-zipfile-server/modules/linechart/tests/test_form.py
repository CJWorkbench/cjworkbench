import datetime
from collections import namedtuple

import numpy as np
import pandas as pd
import pytest
from cjwmodule.testing.i18n import i18n_message

from linechart import Form, GentleValueError, YColumn

Column = namedtuple("Column", ("name", "type", "format"))


# Minimum valid table
min_table = pd.DataFrame({"A": [1, 2], "B": [3, 4]}, dtype=np.number)
min_columns = {"A": Column("A", "number", "{:,}"), "B": Column("B", "number", "{:,}")}


def build_form(**kwargs):
    params = {
        "title": "TITLE",
        "x_axis_label": "X LABEL",
        "y_axis_label": "Y LABEL",
        "x_column": "A",
        "y_columns": [YColumn("B", "#123456")],
    }
    params.update(kwargs)
    return Form(**params)


def test_missing_x_param():
    form = build_form(x_column="")
    with pytest.raises(GentleValueError) as excinfo:
        form.make_chart(
            pd.DataFrame({"A": [1, 2], "B": [2, 3]}),
            {"A": Column("A", "number", "{:}"), "B": Column("B", "number", "{:}")},
        )

    assert excinfo.value.i18n_message == i18n_message("noXAxisError.message")


def test_only_one_x_value():
    form = build_form(x_column="A")
    with pytest.raises(GentleValueError) as excinfo:
        form.make_chart(
            pd.DataFrame({"A": [1, 1], "B": [2, 3]}),
            {"A": Column("A", "number", "{:}"), "B": Column("B", "number", "{:}")},
        )
    assert excinfo.value.i18n_message == i18n_message(
        "onlyOneValueError.message", {"column_name": "A"}
    )


def test_only_one_x_value_not_at_index_0():
    form = build_form(x_column="A")
    with pytest.raises(GentleValueError) as excinfo:
        form.make_chart(
            pd.DataFrame({"A": [np.nan, 1], "B": [2, 3]}),
            {"A": Column("A", "number", "{:}"), "B": Column("B", "number", "{:}")},
        )
    assert excinfo.value.i18n_message == i18n_message(
        "onlyOneValueError.message", {"column_name": "A"}
    )


def test_no_x_values():
    form = build_form(x_column="A")
    with pytest.raises(GentleValueError) as excinfo:
        form.make_chart(
            pd.DataFrame({"A": [np.nan, np.nan], "B": [2, 3]}),
            {"A": Column("A", "number", "{:}"), "B": Column("B", "number", "{:}")},
        )
    assert excinfo.value.i18n_message == i18n_message(
        "noValuesError.message", {"column_name": "A"}
    )


def test_x_numeric():
    form = build_form(x_column="A")
    chart = form.make_chart(min_table, min_columns)
    assert np.array_equal(chart.x_series.series, [1, 2])
    assert chart.x_axis_tick_format == ",r"

    vega = chart.to_vega()
    assert vega["encoding"]["x"]["type"] == "quantitative"
    assert vega["data"]["values"] == [
        {"x": 1, "y0": 3},
        {"x": 2, "y0": 4},
    ]


def test_x_numeric_drop_na_x():
    form = build_form(x_column="A")
    table = pd.DataFrame({"A": [1, np.nan, 3], "B": [3, 4, 5]}, dtype=np.float64)
    chart = form.make_chart(
        table,
        {"A": Column("A", "number", "{:}"), "B": Column("B", "number", "{:}")},
    )
    vega = chart.to_vega()
    assert vega["encoding"]["x"]["type"] == "quantitative"
    assert vega["data"]["values"] == [
        {"x": 1, "y0": 3},
        {"x": 3, "y0": 5},
    ]


def test_x_text():
    form = build_form(x_column="A")
    chart = form.make_chart(
        pd.DataFrame({"A": ["a", "b"], "B": [1, 2]}),
        {"A": Column("A", "text", None), "B": Column("B", "number", "{:}")},
    )
    assert np.array_equal(chart.x_series.series, ["a", "b"])

    vega = chart.to_vega()
    assert vega["encoding"]["x"]["type"] == "ordinal"
    assert vega["data"]["values"] == [
        {"x": "a", "y0": 1},
        {"x": "b", "y0": 2},
    ]


def test_x_text_sort():
    form = build_form(x_column="A")
    chart = form.make_chart(
        pd.DataFrame({"A": ["b", "a"], "B": [1, 2]}),
        {"A": Column("A", "text", None), "B": Column("B", "number", "{:}")},
    )
    assert np.array_equal(chart.x_series.series, ["b", "a"])

    vega = chart.to_vega()
    assert vega["encoding"]["x"]["type"] == "ordinal"
    assert vega["data"]["values"] == [
        {"x": "b", "y0": 1},
        {"x": "a", "y0": 2},
    ]
    assert vega["encoding"]["x"]["sort"] is None


def test_x_text_drop_na_x():
    form = build_form(x_column="A")
    table = pd.DataFrame({"A": ["a", None, "c"], "B": [1, 2, 3]})
    chart = form.make_chart(
        table, {"A": Column("A", "text", None), "B": Column("B", "number", "{:}")}
    )
    assert np.array_equal(chart.x_series.series, ["a", "c"])

    vega = chart.to_vega()
    assert vega["encoding"]["x"]["type"] == "ordinal"
    assert vega["data"]["values"] == [
        {"x": "a", "y0": 1},
        {"x": "c", "y0": 3},
    ]


def test_x_text_too_many_values():
    form = build_form(x_column="A")
    table = pd.DataFrame({"A": ["a"] * 301, "B": [1] * 301})
    with pytest.raises(GentleValueError) as excinfo:
        form.make_chart(
            table,
            {"A": Column("A", "text", None), "B": Column("B", "number", "{:}")},
        )
    assert excinfo.value.i18n_message == i18n_message(
        "tooManyTextValuesError.message",
        {
            "x_column": "A",
            "n_safe_x_values": 301,
        },
    )


def test_y_integer_ticks():
    form = build_form(x_column="A")
    table = pd.DataFrame({"A": [1, 2, 3], "B": [2, 3, 4]})
    chart = form.make_chart(
        table,
        {"A": Column("A", "number", "{:}"), "B": Column("B", "number", "{:,d}")},
    )
    vega = chart.to_vega()
    assert vega["config"]["axisY"]["tickMinStep"] == 1


def test_x_timestamp():
    form = build_form(x_column="A")
    t1 = datetime.datetime(2018, 8, 29, 13, 39)
    t2 = datetime.datetime(2018, 8, 29, 13, 40)
    table = pd.DataFrame({"A": [t1, t2], "B": [3, 4]})
    chart = form.make_chart(
        table,
        # TODO use timestamp format
        {"A": Column("A", "timestamp", None), "B": Column("B", "number", "{:}")},
    )
    assert np.array_equal(
        chart.x_series.series, np.array([t1, t2], dtype="datetime64[ms]")
    )

    vega = chart.to_vega()
    assert vega["encoding"]["x"]["type"] == "temporal"
    assert vega["data"]["values"] == [
        {"x": "2018-08-29T13:39:00Z", "y0": 3},
        {"x": "2018-08-29T13:40:00Z", "y0": 4},
    ]


def test_x_timestamp_custom_ticks():
    form = build_form(x_column="A")
    t1 = datetime.datetime(2020, 12, 7)
    t2 = datetime.datetime(2020, 12, 14)
    table = pd.DataFrame({"A": [t1, t2], "B": [3, 4]})
    chart = form.make_chart(
        table,
        # TODO use timestamp format
        {"A": Column("A", "timestamp", None), "B": Column("B", "number", "{:}")},
    )
    vega = chart.to_vega()
    assert vega["encoding"]["x"]["type"] == "temporal"
    assert vega["encoding"]["x"]["scale"]["domainMin"] == {"expr": "utc(2020, 11, 7)"}
    assert vega["encoding"]["x"]["axis"]["values"] == ["2020-12-07", "2020-12-14"]
    assert (
        vega["encoding"]["x"]["axis"]["labelExpr"]
        == 'utcFormat(datum.value, "%b %-d, %Y")'
    )
    assert vega["data"]["values"] == [
        {"x": "2020-12-07T00:00:00Z", "y0": 3},
        {"x": "2020-12-14T00:00:00Z", "y0": 4},
    ]


def test_x_timestamp_drop_na_x():
    form = build_form(x_column="A")
    t1 = datetime.datetime(2018, 8, 29, 13, 39)
    t2 = datetime.datetime(2018, 8, 29, 13, 40)
    table = pd.DataFrame({"A": [t1, None, t2], "B": [3, 4, 5]})
    chart = form.make_chart(
        table,
        # TODO use timestamp format
        {"A": Column("A", "timestamp", None), "B": Column("B", "number", "{:}")},
    )

    vega = chart.to_vega()
    assert vega["encoding"]["x"]["type"] == "temporal"
    assert vega["data"]["values"] == [
        {"x": "2018-08-29T13:39:00Z", "y0": 3},
        {"x": "2018-08-29T13:40:00Z", "y0": 5},
    ]


def test_drop_missing_y_but_not_x():
    form = build_form(
        x_column="A", y_columns=[YColumn("B", "#123456"), YColumn("C", "#234567")]
    )
    table = pd.DataFrame(
        {"A": [1, 2, 3, 4], "B": [4, np.nan, 6, np.nan], "C": [7, 8, np.nan, np.nan]}
    )
    chart = form.make_chart(
        table,
        {
            "A": Column("A", "number", "{:}"),
            "B": Column("B", "number", "{:}"),
            "C": Column("C", "number", "{:}"),
        },
    )
    vega = chart.to_vega()
    assert vega["data"]["values"] == [
        {"x": 1, "y0": 4.0, "y1": 7.0},
        {"x": 2, "y0": None, "y1": 8.0},
        {"x": 3, "y0": 6.0, "y1": None},
        {"x": 4, "y0": None, "y1": None},
    ]


def test_missing_y_param():
    form = build_form(y_columns=[])
    with pytest.raises(GentleValueError) as excinfo:
        form.make_chart(min_table, min_columns)
    assert excinfo.value.i18n_message == i18n_message("noYAxisError.message")


def test_invalid_y_same_as_x():
    form = build_form(y_columns=[YColumn("A", "#ababab")])
    with pytest.raises(GentleValueError) as excinfo:
        form.make_chart(min_table, min_columns)
    assert excinfo.value.i18n_message == i18n_message(
        "sameAxesError.message", {"column_name": "A"}
    )


def test_invalid_y_missing_values():
    form = build_form(y_columns=[YColumn("B", "#123456"), YColumn("C", "#234567")])
    table = pd.DataFrame(
        {
            "A": [1, 2, np.nan, np.nan, 5],
            "B": [4, np.nan, 6, 7, 8],
            "C": [np.nan, np.nan, 9, 10, np.nan],
        }
    )
    with pytest.raises(GentleValueError) as excinfo:
        form.make_chart(table, min_columns)
    assert excinfo.value.i18n_message == i18n_message(
        "emptyAxisError.message", {"column_name": "C"}
    )


def test_invalid_y_not_numeric():
    form = build_form(y_columns=[YColumn("B", "#123456")])
    table = pd.DataFrame({"A": [1, 2, 3], "B": ["a", "b", "c"]})
    with pytest.raises(GentleValueError) as excinfo:
        form.make_chart(
            table,
            {"A": Column("A", "number", "{:}"), "B": Column("B", "text", None)},
        )
    assert excinfo.value.i18n_message == i18n_message(
        "axisNotNumericError.message", {"column_name": "B"}
    )


def test_default_title_and_labels():
    form = build_form(title="", x_axis_label="", y_axis_label="")
    chart = form.make_chart(min_table, min_columns)
    vega = chart.to_vega()
    assert vega["title"] == "Line Chart"
    assert vega["encoding"]["x"]["axis"]["title"] == "A"
    assert vega["config"]["axisY"]["title"] == "B"
