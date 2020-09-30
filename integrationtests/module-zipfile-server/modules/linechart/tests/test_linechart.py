#!/usr/bin/env python3

from collections import namedtuple
import datetime
import json
import unittest
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from linechart import (
    render,
    Form,
    YColumn,
    GentleValueError,
    migrate_params,
)
from cjwmodule.testing.i18n import i18n_message


Column = namedtuple("Column", ("name", "type", "format"))


# Minimum valid table
min_table = pd.DataFrame({"A": [1, 2], "B": [3, 4]}, dtype=np.number)
min_columns = {"A": Column("A", "number", "{:,}"), "B": Column("B", "number", "{:,}")}


class MigrateParamsTest(unittest.TestCase):
    def test_vneg1(self):
        result = migrate_params(
            {
                "title": "Title",
                "x_axis_label": "X axis",
                "y_axis_label": "Y axis",
                "x_column": "X",
                "y_columns": "",
                "x_data_type": 1,
            }
        )
        self.assertEqual(
            result,
            {
                "title": "Title",
                "x_axis_label": "X axis",
                "y_axis_label": "Y axis",
                "x_column": "X",
                "y_columns": [],
            },
        )

    def test_v0_empty_y_columns(self):
        result = migrate_params(
            {
                "title": "Title",
                "x_axis_label": "X axis",
                "y_axis_label": "Y axis",
                "x_column": "X",
                "y_columns": "",
            }
        )
        self.assertEqual(
            result,
            {
                "title": "Title",
                "x_axis_label": "X axis",
                "y_axis_label": "Y axis",
                "x_column": "X",
                "y_columns": [],
            },
        )

    def test_v0_json_parse(self):
        result = migrate_params(
            {
                "title": "Title",
                "x_axis_label": "X axis",
                "y_axis_label": "Y axis",
                "x_column": "X",
                "y_columns": '[{"column": "X", "color": "#111111"}]',
            }
        )
        self.assertEqual(
            result,
            {
                "title": "Title",
                "x_axis_label": "X axis",
                "y_axis_label": "Y axis",
                "x_column": "X",
                "y_columns": [{"column": "X", "color": "#111111"}],
            },
        )

    def test_v1_no_op(self):
        result = migrate_params(
            {
                "title": "Title",
                "x_axis_label": "X axis",
                "y_axis_label": "Y axis",
                "x_column": "X",
                "y_columns": [{"column": "X", "color": "#111111"}],
            }
        )
        self.assertEqual(
            result,
            {
                "title": "Title",
                "x_axis_label": "X axis",
                "y_axis_label": "Y axis",
                "x_column": "X",
                "y_columns": [{"column": "X", "color": "#111111"}],
            },
        )


class FormTest(unittest.TestCase):
    def assertResult(self, result, expected):
        assert_frame_equal(result[0], expected[0])
        self.assertEqual(result[1], expected[1])
        self.assertEqual(result[2], expected[2])

    def build_form(self, **kwargs):
        params = {
            "title": "TITLE",
            "x_axis_label": "X LABEL",
            "y_axis_label": "Y LABEL",
            "x_column": "A",
            "y_columns": [YColumn("B", "#123456")],
        }
        params.update(kwargs)
        return Form(**params)

    def test_missing_x_param(self):
        form = self.build_form(x_column="")
        with self.assertRaises(GentleValueError) as cm:
            form.make_chart(
                pd.DataFrame({"A": [1, 2], "B": [2, 3]}),
                {"A": Column("A", "number", "{:}"), "B": Column("B", "number", "{:}")},
            )

        self.assertEqual(
            cm.exception.i18n_message, i18n_message("noXAxisError.message")
        )

    def test_only_one_x_value(self):
        form = self.build_form(x_column="A")
        with self.assertRaises(GentleValueError) as cm:
            form.make_chart(
                pd.DataFrame({"A": [1, 1], "B": [2, 3]}),
                {"A": Column("A", "number", "{:}"), "B": Column("B", "number", "{:}")},
            )
        self.assertEqual(
            cm.exception.i18n_message,
            i18n_message("onlyOneValueError.message", {"column_name": "A"}),
        )

    def test_only_one_x_value_not_at_index_0(self):
        form = self.build_form(x_column="A")
        with self.assertRaises(GentleValueError) as cm:
            form.make_chart(
                pd.DataFrame({"A": [np.nan, 1], "B": [2, 3]}),
                {"A": Column("A", "number", "{:}"), "B": Column("B", "number", "{:}")},
            )
        self.assertEqual(
            cm.exception.i18n_message,
            i18n_message("onlyOneValueError.message", {"column_name": "A"}),
        )

    def test_no_x_values(self):
        form = self.build_form(x_column="A")
        with self.assertRaises(GentleValueError) as cm:
            form.make_chart(
                pd.DataFrame({"A": [np.nan, np.nan], "B": [2, 3]}),
                {"A": Column("A", "number", "{:}"), "B": Column("B", "number", "{:}")},
            )
        self.assertEqual(
            cm.exception.i18n_message,
            i18n_message("noValuesError.message", {"column_name": "A"}),
        )

    def test_x_numeric(self):
        form = self.build_form(x_column="A")
        chart = form.make_chart(min_table, min_columns)
        assert np.array_equal(chart.x_series.series, [1, 2])
        self.assertEqual(chart.x_axis_tick_format, ",r")

        vega = chart.to_vega()
        self.assertEqual(vega["encoding"]["x"]["type"], "quantitative")
        self.assertEqual(
            vega["data"]["values"],
            [{"x": 1, "line": "B", "y": 3}, {"x": 2, "line": "B", "y": 4}],
        )

    def test_x_numeric_drop_na_x(self):
        form = self.build_form(x_column="A")
        table = pd.DataFrame({"A": [1, np.nan, 3], "B": [3, 4, 5]}, dtype=np.number)
        chart = form.make_chart(
            table,
            {"A": Column("A", "number", "{:}"), "B": Column("B", "number", "{:}")},
        )
        vega = chart.to_vega()
        self.assertEqual(vega["encoding"]["x"]["type"], "quantitative")
        self.assertEqual(
            vega["data"]["values"],
            [{"x": 1, "line": "B", "y": 3}, {"x": 3, "line": "B", "y": 5}],
        )

    def test_x_text(self):
        form = self.build_form(x_column="A")
        chart = form.make_chart(
            pd.DataFrame({"A": ["a", "b"], "B": [1, 2]}),
            {"A": Column("A", "text", None), "B": Column("B", "number", "{:}")},
        )
        assert np.array_equal(chart.x_series.series, ["a", "b"])

        vega = chart.to_vega()
        self.assertEqual(vega["encoding"]["x"]["type"], "ordinal")
        self.assertEqual(
            vega["data"]["values"],
            [{"x": "a", "line": "B", "y": 1}, {"x": "b", "line": "B", "y": 2}],
        )

    def test_x_text_sort(self):
        form = self.build_form(x_column="A")
        chart = form.make_chart(
            pd.DataFrame({"A": ["b", "a"], "B": [1, 2]}),
            {"A": Column("A", "text", None), "B": Column("B", "number", "{:}")},
        )
        assert np.array_equal(chart.x_series.series, ["b", "a"])

        vega = chart.to_vega()
        self.assertEqual(vega["encoding"]["x"]["type"], "ordinal")
        self.assertEqual(
            vega["data"]["values"],
            [{"x": "b", "line": "B", "y": 1}, {"x": "a", "line": "B", "y": 2}],
        )
        self.assertEqual(vega["encoding"]["x"]["sort"], None)

    def test_x_text_drop_na_x(self):
        form = self.build_form(x_column="A")
        table = pd.DataFrame({"A": ["a", None, "c"], "B": [1, 2, 3]})
        chart = form.make_chart(
            table, {"A": Column("A", "text", None), "B": Column("B", "number", "{:}")}
        )
        assert np.array_equal(chart.x_series.series, ["a", None, "c"])

        vega = chart.to_vega()
        self.assertEqual(vega["encoding"]["x"]["type"], "ordinal")
        self.assertEqual(
            vega["data"]["values"],
            [{"x": "a", "line": "B", "y": 1}, {"x": "c", "line": "B", "y": 3}],
        )

    def test_x_text_too_many_values(self):
        form = self.build_form(x_column="A")
        table = pd.DataFrame({"A": ["a"] * 301, "B": [1] * 301})
        with self.assertRaises(GentleValueError) as cm:
            form.make_chart(
                table,
                {"A": Column("A", "text", None), "B": Column("B", "number", "{:}")},
            )
        self.assertEqual(
            cm.exception.i18n_message,
            i18n_message(
                "tooManyTextValuesError.message",
                {
                    "x_column": "A",
                    "n_safe_x_values": 301,
                },
            ),
        )

    def test_x_datetime(self):
        form = self.build_form(x_column="A")
        t1 = datetime.datetime(2018, 8, 29, 13, 39)
        t2 = datetime.datetime(2018, 8, 29, 13, 40)
        table = pd.DataFrame({"A": [t1, t2], "B": [3, 4]})
        chart = form.make_chart(
            table,
            # TODO use datetime format
            {"A": Column("A", "datetime", None), "B": Column("B", "number", "{:}")},
        )
        assert np.array_equal(
            chart.x_series.series, np.array([t1, t2], dtype="datetime64[ms]")
        )

        vega = chart.to_vega()
        self.assertEqual(vega["encoding"]["x"]["type"], "temporal")
        self.assertEqual(
            vega["data"]["values"],
            [
                {"x": "2018-08-29T13:39:00Z", "line": "B", "y": 3},
                {"x": "2018-08-29T13:40:00Z", "line": "B", "y": 4},
            ],
        )

    def test_x_timestamp(self):
        form = self.build_form(x_column="A")
        t1 = datetime.datetime(2018, 8, 29, 13, 39)
        t2 = datetime.datetime(2018, 8, 29, 13, 40)
        table = pd.DataFrame({"A": [t1, t2], "B": [3, 4]})
        chart = form.make_chart(
            table,
            # TODO use datetime format
            {"A": Column("A", "timestamp", None), "B": Column("B", "number", "{:}")},
        )
        assert np.array_equal(
            chart.x_series.series, np.array([t1, t2], dtype="datetime64[ms]")
        )

        vega = chart.to_vega()
        self.assertEqual(vega["encoding"]["x"]["type"], "temporal")
        self.assertEqual(
            vega["data"]["values"],
            [
                {"x": "2018-08-29T13:39:00Z", "line": "B", "y": 3},
                {"x": "2018-08-29T13:40:00Z", "line": "B", "y": 4},
            ],
        )

    def test_x_timestamp_drop_na_x(self):
        form = self.build_form(x_column="A")
        t1 = datetime.datetime(2018, 8, 29, 13, 39)
        t2 = datetime.datetime(2018, 8, 29, 13, 40)
        table = pd.DataFrame({"A": [t1, None, t2], "B": [3, 4, 5]})
        chart = form.make_chart(
            table,
            # TODO use datetime format
            {"A": Column("A", "timestamp", None), "B": Column("B", "number", "{:}")},
        )

        vega = chart.to_vega()
        self.assertEqual(vega["encoding"]["x"]["type"], "temporal")
        self.assertEqual(
            vega["data"]["values"],
            [
                {"x": "2018-08-29T13:39:00Z", "line": "B", "y": 3},
                {"x": "2018-08-29T13:40:00Z", "line": "B", "y": 5},
            ],
        )

    def test_drop_missing_y_but_not_x(self):
        form = self.build_form(
            x_column="A", y_columns=[YColumn("B", "#123456"), YColumn("C", "#234567")]
        )
        table = pd.DataFrame({"A": [1, 2, 3], "B": [4, np.nan, 6], "C": [7, 8, np.nan]})
        chart = form.make_chart(
            table,
            {
                "A": Column("A", "number", "{:}"),
                "B": Column("B", "number", "{:}"),
                "C": Column("C", "number", "{:}"),
            },
        )
        vega = chart.to_vega()
        self.assertEqual(
            vega["data"]["values"],
            [
                {"x": 1, "line": "B", "y": 4.0},
                {"x": 3, "line": "B", "y": 6.0},
                {"x": 1, "line": "C", "y": 7.0},
                {"x": 2, "line": "C", "y": 8.0},
            ],
        )

    def test_missing_y_param(self):
        form = self.build_form(y_columns=[])
        with self.assertRaises(GentleValueError) as cm:
            form.make_chart(min_table, min_columns)
        self.assertEqual(
            cm.exception.i18n_message, i18n_message("noYAxisError.message")
        )

    def test_invalid_y_same_as_x(self):
        form = self.build_form(y_columns=[YColumn("A", "#ababab")])
        with self.assertRaises(GentleValueError) as cm:
            form.make_chart(min_table, min_columns)
        self.assertEqual(
            cm.exception.i18n_message,
            i18n_message("sameAxesError.message", {"column_name": "A"}),
        )

    def test_invalid_y_missing_values(self):
        form = self.build_form(
            y_columns=[YColumn("B", "#123456"), YColumn("C", "#234567")]
        )
        table = pd.DataFrame(
            {
                "A": [1, 2, np.nan, np.nan, 5],
                "B": [4, np.nan, 6, 7, 8],
                "C": [np.nan, np.nan, 9, 10, np.nan],
            }
        )
        with self.assertRaises(GentleValueError) as cm:
            form.make_chart(table, min_columns)
        self.assertEqual(
            cm.exception.i18n_message,
            i18n_message("emptyAxisError.message", {"column_name": "C"}),
        )

    def test_invalid_y_not_numeric(self):
        form = self.build_form(y_columns=[YColumn("B", "#123456")])
        table = pd.DataFrame({"A": [1, 2, 3], "B": ["a", "b", "c"]})
        with self.assertRaises(GentleValueError) as cm:
            form.make_chart(
                table,
                {"A": Column("A", "number", "{:}"), "B": Column("B", "text", None)},
            )
        self.assertEqual(
            cm.exception.i18n_message,
            i18n_message("axisNotNumericError.message", {"column_name": "B"}),
        )

    def test_default_title_and_labels(self):
        form = self.build_form(title="", x_axis_label="", y_axis_label="")
        chart = form.make_chart(min_table, min_columns)
        vega = chart.to_vega()
        self.assertEqual(vega["title"], "Line Chart")
        self.assertEqual(vega["encoding"]["x"]["axis"]["title"], "A")
        self.assertEqual(vega["encoding"]["y"]["axis"]["title"], "B")

    def test_integration_empty_params(self):
        DefaultParams = {
            "title": "",
            "x_axis_label": "",
            "y_axis_label": "",
            "x_column": "",
            "y_columns": [],
        }
        table = pd.DataFrame({"A": [1, 2], "B": [2, 3]})
        result = render(
            table,
            DefaultParams,
            input_columns={
                "A": Column("A", "number", "{:,d}"),
                "B": Column("B", "number", "{:,.2f}"),
            },
        )
        self.assertResult(
            result,
            (
                table,
                i18n_message("noXAxisError.message"),
                {"error": "Please correct the error in this step's data or parameters"},
            ),
        )

    def test_integration(self):
        table = pd.DataFrame({"A": [1, 2], "B": [2, 3]})
        result = render(
            table,
            {
                "title": "TITLE",
                "x_column": "A",
                "y_columns": [{"column": "B", "color": "#123456"}],
                "x_axis_label": "X LABEL",
                "y_axis_label": "Y LABEL",
            },
            input_columns={
                "A": Column("A", "number", "{:,d}"),
                "B": Column("B", "number", "{:,.2f}"),
            },
        )
        assert_frame_equal(result[0], table)
        self.assertEqual(result[1], "")
        text = json.dumps(result[2])
        # We won't snapshot the chart: that's too brittle. (We change styling
        # more often than we change logic.) But let's make sure all our
        # parameters are in the JSON.
        self.assertIn('"TITLE"', text)
        self.assertIn('"X LABEL"', text)
        self.assertIn('"Y LABEL"', text)
        self.assertIn('"#123456"', text)
        self.assertRegex(text, r".*:\s*3[,}]")
