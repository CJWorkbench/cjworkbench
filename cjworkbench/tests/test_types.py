from datetime import datetime as dt
import unittest
from unittest import mock
import numpy as np
import pandas as pd
from pandas.testing import assert_series_equal, assert_frame_equal
from cjworkbench.types import Column, ColumnType, ProcessResult, QuickFix, TableShape


class ColumnTypeTextTests(unittest.TestCase):
    def test_text_type(self):
        series = pd.Series(["x", np.nan, "z"])
        column_type = ColumnType.TEXT()
        result = column_type.format_series(series)
        assert_series_equal(result, pd.Series(["x", np.nan, "z"]))


class ColumnTypeNumberTests(unittest.TestCase):
    def test_default_format(self):
        series = pd.Series([1.1, 2.231, np.nan])
        column_type = ColumnType.NUMBER()
        result = column_type.format_series(series)
        assert_series_equal(result, pd.Series(["1.1", "2.231", np.nan]))

    def test_format_whole_float_as_int(self):
        """
        Mimic d3-format, which cannot differentiate between float and int.
        """
        series = pd.Series([1.1, 2.0, 123456789.0])
        column_type = ColumnType.NUMBER("{:,}")
        result = column_type.format_series(series)
        assert_series_equal(result, pd.Series(["1.1", "2", "123,456,789"]))

    def test_custom_format(self):
        series = pd.Series([1.1, 2231, np.nan, 0.123])
        column_type = ColumnType.NUMBER(format="${:0,.2f}")
        result = column_type.format_series(series)
        assert_series_equal(result, pd.Series(["$1.10", "$2,231.00", np.nan, "$0.12"]))

    def test_format_int_as_float(self):
        series = pd.Series([1, 2, 3, 4], dtype=int)
        column_type = ColumnType.NUMBER(format="{:.1f}")
        result = column_type.format_series(series)
        assert_series_equal(result, pd.Series(["1.0", "2.0", "3.0", "4.0"]))

    def test_format_float_as_int(self):
        series = pd.Series([1.1])
        column_type = ColumnType.NUMBER(format="{:d}")
        result = column_type.format_series(series)
        assert_series_equal(result, pd.Series(["1"]))

    def test_format_percent(self):
        series = pd.Series([0.3, 11.111, 0.0001, np.nan])
        column_type = ColumnType.NUMBER(format="{:,.1%}")
        result = column_type.format_series(series)
        assert_series_equal(result, pd.Series(["30.0%", "1,111.1%", "0.0%", np.nan]))

    def test_format_int_as_percent(self):
        series = pd.Series([1, 11])
        column_type = ColumnType.NUMBER(format="{:,.1%}")
        result = column_type.format_series(series)
        assert_series_equal(result, pd.Series(["100.0%", "1,100.0%"]))

    def test_format_zero_length_becomes_str(self):
        # (even though there's no way for pandas to detect type of result)
        # (luckily, pandas defaults to `object`)
        series = pd.Series([], dtype=np.int64)
        result = ColumnType.NUMBER().format_series(series)
        assert_series_equal(result, pd.Series([], dtype=object))

    def test_format_nulls_becomes_str(self):
        series = pd.Series([np.nan, np.nan], dtype=np.float64)
        result = ColumnType.NUMBER().format_series(series)
        assert_series_equal(result, pd.Series([np.nan, np.nan], dtype=object))

    def test_format_too_many_arguments(self):
        with self.assertRaisesRegex(ValueError, "Can only format one number"):
            ColumnType.NUMBER("{:d}{:f}")

    def test_format_disallow_non_format(self):
        with self.assertRaisesRegex(ValueError, 'Format must look like "{:...}"'):
            ColumnType.NUMBER("%d")

    def test_format_disallow_field_number(self):
        with self.assertRaisesRegex(
            ValueError, "Field names or numbers are not allowed"
        ):
            ColumnType.NUMBER("{0:f}")

    def test_format_disallow_field_name(self):
        with self.assertRaisesRegex(
            ValueError, "Field names or numbers are not allowed"
        ):
            ColumnType.NUMBER("{value:f}")

    def test_format_disallow_field_converter(self):
        with self.assertRaisesRegex(ValueError, "Field converters are not allowed"):
            ColumnType.NUMBER("{!r:f}")

    def test_format_disallow_invalid_type(self):
        with self.assertRaisesRegex(ValueError, "Unknown format code 'T'"):
            ColumnType.NUMBER("{:T}")


class ColumnTypeDatetimeTests(unittest.TestCase):
    def test_format(self):
        series = pd.Series(
            [dt(1999, 2, 3, 4, 5, 6, 7), np.nan, dt(2000, 3, 4, 5, 6, 7, 8)]
        )
        column_type = ColumnType.DATETIME()
        result = column_type.format_series(series)
        assert_series_equal(
            result,
            pd.Series(
                ["1999-02-03T04:05:06.000007Z", np.nan, "2000-03-04T05:06:07.000008Z"]
            ),
        )


class ProcessResultTests(unittest.TestCase):
    def test_eq_none(self):
        self.assertNotEqual(ProcessResult(), None)

    def test_ctor_infer_columns(self):
        result = ProcessResult(
            pd.DataFrame(
                {
                    "A": [1, 2],
                    "B": ["x", "y"],
                    "C": [np.nan, dt(2019, 3, 3, 4, 5, 6, 7)],
                }
            )
        )
        self.assertEqual(
            result.columns,
            [
                Column("A", ColumnType.NUMBER()),
                Column("B", ColumnType.TEXT()),
                Column("C", ColumnType.DATETIME()),
            ],
        )

    def test_coerce_infer_columns(self):
        table = pd.DataFrame({"A": [1, 2], "B": ["x", "y"]})
        result = ProcessResult.coerce(table)
        self.assertEqual(
            result.columns,
            [Column("A", ColumnType.NUMBER()), Column("B", ColumnType.TEXT())],
        )

    def test_coerce_infer_columns_with_format(self):
        table = pd.DataFrame({"A": [1, 2], "B": ["x", "y"]})
        result = ProcessResult.coerce(
            {"dataframe": table, "column_formats": {"A": "{:,d}"}}
        )
        self.assertEqual(
            result.columns,
            [
                Column("A", ColumnType.NUMBER(format="{:,d}")),
                Column("B", ColumnType.TEXT()),
            ],
        )

    def test_coerce_infer_columns_invalid_format_is_error(self):
        table = pd.DataFrame({"A": [1, 2]})
        with self.assertRaisesRegex(ValueError, 'Format must look like "{:...}"'):
            ProcessResult.coerce({"dataframe": table, "column_formats": {"A": "x"}})

    def test_coerce_infer_columns_wrong_type_format_is_error(self):
        table = pd.DataFrame({"A": [1, 2]})
        with self.assertRaisesRegex(ValueError, "Format must be str"):
            ProcessResult.coerce({"dataframe": table, "column_formats": {"A": {}}})

    def test_coerce_infer_columns_text_format_is_error(self):
        table = pd.DataFrame({"A": [1, 2], "B": ["x", "y"]})
        with self.assertRaisesRegex(
            ValueError,
            '"format" not allowed for column "B" because it is of type "text"',
        ):
            ProcessResult.coerce({"dataframe": table, "column_formats": {"B": "{:,d}"}})

    def test_coerce_infer_columns_try_fallback_columns(self):
        table = pd.DataFrame({"A": [1, 2], "B": ["x", "y"]})
        result = ProcessResult.coerce(
            table,
            try_fallback_columns=[
                Column("A", ColumnType.NUMBER("{:,d}")),
                Column("B", ColumnType.TEXT()),
            ],
        )
        self.assertEqual(
            result.columns,
            [Column("A", ColumnType.NUMBER("{:,d}")), Column("B", ColumnType.TEXT())],
        )

    def test_coerce_infer_columns_try_fallback_columns_ignore_wrong_type(self):
        table = pd.DataFrame({"A": [1, 2], "B": ["x", "y"]})
        result = ProcessResult.coerce(
            table,
            try_fallback_columns=[
                Column("A", ColumnType.TEXT()),
                Column("B", ColumnType.NUMBER()),
            ],
        )
        self.assertEqual(
            result.columns,
            [Column("A", ColumnType.NUMBER()), Column("B", ColumnType.TEXT())],
        )

    def test_coerce_infer_columns_format_supercedes_try_fallback_columns(self):
        table = pd.DataFrame({"A": [1, 2]})
        result = ProcessResult.coerce(
            {
                "dataframe": pd.DataFrame({"A": [1, 2]}),
                "column_formats": {"A": "{:,d}"},
            },
            try_fallback_columns=[Column("A", ColumnType.NUMBER("{:,.2f}"))],
        )
        self.assertEqual(result.columns, [Column("A", ColumnType.NUMBER("{:,d}"))])

    def test_coerce_validate_index(self):
        with self.assertRaisesRegex(ValueError, "must use the default RangeIndex"):
            ProcessResult.coerce(pd.DataFrame({"A": [1, 2]})[1:])

    def test_coerce_validate_processresult(self):
        """ProcessResult.coerce(<ProcessResult>) should raise on error."""
        # render() gets access to a fetch_result. Imagine this module:
        #
        # def render(table, params, *, fetch_result):
        #     fetch_result.dataframe.drop(0, inplace=True)
        #     return fetch_result  # invalid index
        #
        # We could (and maybe should) avoid this by banning ProcessResult
        # retvals from `render()`. But to be consistent we'd need to ban
        # ProcessResult retvals from `fetch()`; and that'd take a few hours.
        #
        # TODO ban `ProcessResult` retvals from `fetch()`, then raise
        # Valueerror on ProcessResult.coerce(<ProcessResult>).
        fetch_result = ProcessResult(pd.DataFrame({"A": [1, 2, 3]}))
        fetch_result.dataframe.drop(0, inplace=True)  # bad index
        with self.assertRaisesRegex(ValueError, "must use the default RangeIndex"):
            ProcessResult.coerce(fetch_result)

    def test_coerce_validate_non_str_objects(self):
        with self.assertRaisesRegex(ValueError, "must all be str"):
            ProcessResult.coerce(pd.DataFrame({"foo": ["a", 1]}))

    def test_coerce_validate_empty_categories_with_wrong_dtype(self):
        with self.assertRaisesRegex(ValueError, "must have dtype=object"):
            ProcessResult.coerce(
                pd.DataFrame({"foo": [np.nan]}, dtype=float).astype("category")
            )

    def test_coerce_validate_non_str_categories(self):
        with self.assertRaisesRegex(ValueError, "must all be str"):
            ProcessResult.coerce(pd.DataFrame({"foo": ["a", 1]}, dtype="category"))

    def test_coerce_validate_unused_categories(self):
        with self.assertRaisesRegex(ValueError, "unused category 'b'"):
            ProcessResult.coerce(
                pd.DataFrame({"foo": ["a", "a"]}, dtype=pd.CategoricalDtype(["a", "b"]))
            )

    def test_coerce_validate_null_is_not_a_category(self):
        # pd.CategoricalDtype means storing nulls as -1. Don't consider -1 when
        # counting the used categories.
        with self.assertRaisesRegex(ValueError, "unused category 'b'"):
            ProcessResult.coerce(
                pd.DataFrame(
                    {"foo": ["a", None]}, dtype=pd.CategoricalDtype(["a", "b"])
                )
            )

    def test_coerce_validate_empty_categories(self):
        df = pd.DataFrame({"A": []}, dtype="category")
        result = ProcessResult.coerce(df)
        assert_frame_equal(result.dataframe, df)

    def test_coerce_validate_unique_colnames(self):
        dataframe = pd.DataFrame({"A": [1], "B": [2]})
        dataframe.columns = ["A", "A"]
        with self.assertRaisesRegex(ValueError, "duplicate column name"):
            ProcessResult.coerce(dataframe)

    def test_coerce_validate_empty_colname(self):
        dataframe = pd.DataFrame({"": [1], "B": [2]})
        with self.assertRaisesRegex(ValueError, "empty column name"):
            ProcessResult.coerce(dataframe)

    def test_coerce_validate_numpy_dtype(self):
        # Numpy dtypes should be treated just like pandas dtypes.
        dataframe = pd.DataFrame({"A": np.array([1, 2, 3])})
        result = ProcessResult.coerce(dataframe)
        assert_frame_equal(result.dataframe, dataframe)

    def test_coerce_validate_unsupported_dtype(self):
        dataframe = pd.DataFrame(
            {
                # A type we never plan on supporting
                "A": pd.Series([pd.Interval(0, 1)], dtype="interval")
            }
        )
        with self.assertRaisesRegex(ValueError, "unsupported dtype"):
            ProcessResult.coerce(dataframe)

    def test_coerce_validate_datetime64tz_unsupported(self):
        dataframe = pd.DataFrame(
            {
                # We don't support datetimes with time zone data ... yet
                "A": pd.Series([pd.to_datetime("2019-04-23T12:34:00-0500")])
            }
        )
        with self.assertRaisesRegex(ValueError, "unsupported dtype"):
            ProcessResult.coerce(dataframe)

    def test_coerce_validate_nullable_int_unsupported(self):
        dataframe = pd.DataFrame(
            {
                # We don't support nullable integer columns ... yet
                "A": pd.Series([1, np.nan], dtype=pd.Int64Dtype())
            }
        )
        with self.assertRaisesRegex(ValueError, "unsupported dtype"):
            ProcessResult.coerce(dataframe)

    def test_coerce_validate_infinity_not_supported(self):
        # Make 'A': [1, -inf, +inf, nan]
        num = pd.Series([1, -2, 3, np.nan])
        denom = pd.Series([1, 0, 0, 1])
        dataframe = pd.DataFrame({"A": num / denom})
        with self.assertRaisesRegex(
            ValueError,
            (
                "invalid value -inf in column 'A', row 1 "
                "\(infinity is not supported\)"
            ),
        ):
            ProcessResult.coerce(dataframe)

    def test_coerce_validate_unsupported_numpy_dtype_unsupported(self):
        # We can't check if a numpy dtype == 'category'.
        # https://github.com/pandas-dev/pandas/issues/16697
        arr = np.array([1, 2, 3]).astype("complex")  # we don't support complex
        dataframe = pd.DataFrame({"A": arr})
        with self.assertRaisesRegex(ValueError, "unsupported dtype"):
            ProcessResult.coerce(dataframe)

    def test_coerce_validate_colnames_dtype_object(self):
        with self.assertRaisesRegex(ValueError, "column names"):
            # df.columns is numeric
            ProcessResult.coerce(pd.DataFrame({1: [1]}))

    def test_coerce_validate_colnames_all_str(self):
        with self.assertRaisesRegex(ValueError, "column names"):
            # df.columns is object, but not all are str
            ProcessResult.coerce(pd.DataFrame({"A": [1], 2: [2]}))

    def test_coerce_none(self):
        result = ProcessResult.coerce(None)
        expected = ProcessResult(dataframe=pd.DataFrame())
        self.assertEqual(result, expected)

    def test_coerce_processresult(self):
        expected = ProcessResult()
        result = ProcessResult.coerce(expected)
        self.assertIs(result, expected)

    def test_coerce_dataframe(self):
        df = pd.DataFrame({"foo": ["bar"]})
        expected = ProcessResult(dataframe=df)
        result = ProcessResult.coerce(df)
        self.assertEqual(result, expected)

    def test_coerce_str(self):
        expected = ProcessResult(error="yay")
        result = ProcessResult.coerce("yay")
        self.assertEqual(result, expected)

    def test_coerce_tuple_dataframe_none(self):
        df = pd.DataFrame({"foo": ["bar"]})
        expected = ProcessResult(dataframe=df)
        result = ProcessResult.coerce((df, None))
        self.assertEqual(result, expected)

    def test_coerce_tuple_dataframe_str(self):
        df = pd.DataFrame({"foo": ["bar"]})
        expected = ProcessResult(dataframe=df, error="hi")
        result = ProcessResult.coerce((df, "hi"))
        self.assertEqual(result, expected)

    def test_coerce_tuple_none_str(self):
        expected = ProcessResult(error="hi")
        result = ProcessResult.coerce((None, "hi"))
        self.assertEqual(result, expected)

    def test_coerce_tuple_dataframe_str_dict(self):
        df = pd.DataFrame({"foo": ["bar"]})
        expected = ProcessResult(df, "hi", json={"a": "b"})
        result = ProcessResult.coerce((df, "hi", {"a": "b"}))
        self.assertEqual(result, expected)

    def test_coerce_tuple_dataframe_str_none(self):
        df = pd.DataFrame({"foo": ["bar"]})
        expected = ProcessResult(df, "hi")
        result = ProcessResult.coerce((df, "hi", None))
        self.assertEqual(result, expected)

    def test_coerce_tuple_dataframe_none_dict(self):
        df = pd.DataFrame({"foo": ["bar"]})
        expected = ProcessResult(df, "", json={"a": "b"})
        result = ProcessResult.coerce((df, None, {"a": "b"}))
        self.assertEqual(result, expected)

    def test_coerce_tuple_dataframe_none_none(self):
        df = pd.DataFrame({"foo": ["bar"]})
        expected = ProcessResult(df)
        result = ProcessResult.coerce((df, None, None))
        self.assertEqual(result, expected)

    def test_coerce_tuple_none_str_dict(self):
        expected = ProcessResult(error="hi", json={"a": "b"})
        result = ProcessResult.coerce((None, "hi", {"a": "b"}))
        self.assertEqual(result, expected)

    def test_coerce_tuple_none_str_none(self):
        expected = ProcessResult(error="hi")
        result = ProcessResult.coerce((None, "hi", None))
        self.assertEqual(result, expected)

    def test_coerce_tuple_none_none_dict(self):
        expected = ProcessResult(json={"a": "b"})
        result = ProcessResult.coerce((None, None, {"a": "b"}))
        self.assertEqual(result, expected)

    def test_coerce_tuple_none_none_none(self):
        expected = ProcessResult()
        result = ProcessResult.coerce((None, None, None))
        self.assertEqual(result, expected)

    def test_coerce_bad_tuple(self):
        result = ProcessResult.coerce(("foo", "bar", "baz", "moo"))
        self.assertIsNotNone(result.error)

    def test_coerce_2tuple_no_dataframe(self):
        result = ProcessResult.coerce(("foo", "bar"))
        self.assertIsNotNone(result.error)

    def test_coerce_3tuple_no_dataframe(self):
        result = ProcessResult.coerce(("foo", "bar", {"a": "b"}))
        self.assertIsNotNone(result.error)

    def test_coerce_dict_with_quickfix_tuple(self):
        dataframe = pd.DataFrame({"A": [1, 2]})
        quick_fix = QuickFix(
            "Hi", "prependModule", ["texttodate", {"column": "created_at"}]
        )
        result = ProcessResult.coerce(
            {
                "dataframe": dataframe,
                "error": "an error",
                "json": {"foo": "bar"},
                "quick_fixes": [
                    ("Hi", "prependModule", "texttodate", {"column": "created_at"})
                ],
            }
        )
        expected = ProcessResult(
            dataframe, "an error", json={"foo": "bar"}, quick_fixes=[quick_fix]
        )
        self.assertEqual(result, expected)

    def test_coerce_dict_with_quickfix_tuple_not_json_serializable(self):
        dataframe = pd.DataFrame({"A": [1, 2]})
        with self.assertRaisesRegex(ValueError, "JSON serializable"):
            ProcessResult.coerce(
                {
                    "dataframe": dataframe,
                    "error": "an error",
                    "json": {"foo": "bar"},
                    "quick_fixes": [
                        (
                            "Hi",
                            "prependModule",
                            "texttodate",
                            {"columns": pd.Index(["created_at"])},
                        )
                    ],
                }
            )

    def test_coerce_dict_with_quickfix_dict(self):
        dataframe = pd.DataFrame({"A": [1, 2]})
        quick_fix = QuickFix(
            "Hi", "prependModule", ["texttodate", {"column": "created_at"}]
        )
        result = ProcessResult.coerce(
            {
                "dataframe": dataframe,
                "error": "an error",
                "json": {"foo": "bar"},
                "quick_fixes": [
                    {
                        "text": "Hi",
                        "action": "prependModule",
                        "args": ["texttodate", {"column": "created_at"}],
                    }
                ],
            }
        )
        expected = ProcessResult(
            dataframe, "an error", json={"foo": "bar"}, quick_fixes=[quick_fix]
        )
        self.assertEqual(result, expected)

    def test_coerce_dict_bad_quickfix_dict(self):
        with self.assertRaises(ValueError):
            ProcessResult.coerce(
                {
                    "error": "an error",
                    "quick_fixes": [
                        {
                            "text": "Hi",
                            "action": "prependModule",
                            "arguments": ["texttodate", {"column": "created_at"}],
                        }
                    ],
                }
            )

    def test_coerce_dict_quickfix_dict_has_class_not_json(self):
        with self.assertRaisesRegex(ValueError, "JSON serializable"):
            ProcessResult.coerce(
                {
                    "error": "an error",
                    "quick_fixes": [
                        {
                            "text": "Hi",
                            "action": "prependModule",
                            "args": [
                                "texttodate",
                                {"columns": pd.Index(["created_at"])},
                            ],
                        }
                    ],
                }
            )

    def test_coerce_dict_wrong_key(self):
        with self.assertRaises(ValueError):
            ProcessResult.coerce({"table": pd.DataFrame({"A": [1]})})

    def test_coerce_empty_dict(self):
        result = ProcessResult.coerce({})
        expected = ProcessResult()
        self.assertEqual(result, expected)

    def test_coerce_invalid_value(self):
        result = ProcessResult.coerce([None, "foo"])
        self.assertIsNotNone(result.error)

    def test_status_ok(self):
        result = ProcessResult(pd.DataFrame({"A": [1]}), "")
        self.assertEqual(result.status, "ok")

    def test_status_ok_with_warning(self):
        result = ProcessResult(pd.DataFrame({"A": [1]}), "warning")
        self.assertEqual(result.status, "ok")

    def test_status_ok_with_no_rows(self):
        result = ProcessResult(pd.DataFrame({"A": []}), "")
        self.assertEqual(result.status, "ok")

    def test_status_error(self):
        result = ProcessResult(pd.DataFrame(), "error")
        self.assertEqual(result.status, "error")

    def test_status_unreachable(self):
        result = ProcessResult(pd.DataFrame(), "")
        self.assertEqual(result.status, "unreachable")

    def test_truncate_too_big_no_error(self):
        expected_df = pd.DataFrame({"foo": ["bar", "baz"]})
        expected = ProcessResult(
            dataframe=expected_df, error="Truncated output from 3 rows to 2"
        )

        with mock.patch("django.conf.settings.MAX_ROWS_PER_TABLE", 2):
            result_df = pd.DataFrame({"foo": ["bar", "baz", "moo"]})
            result = ProcessResult(result_df, error="")
            result.truncate_in_place_if_too_big()

        self.assertEqual(result, expected)

    def test_truncate_too_big_and_error(self):
        expected_df = pd.DataFrame({"foo": ["bar", "baz"]})
        expected = ProcessResult(
            dataframe=expected_df, error="Some error\nTruncated output from 3 rows to 2"
        )

        with mock.patch("django.conf.settings.MAX_ROWS_PER_TABLE", 2):
            result_df = pd.DataFrame({"foo": ["bar", "baz", "moo"]})
            result = ProcessResult(result_df, error="Some error")
            result.truncate_in_place_if_too_big()

        self.assertEqual(result, expected)

    def test_truncate_too_big_remove_unused_categories(self):
        with mock.patch("django.conf.settings.MAX_ROWS_PER_TABLE", 2):
            result_df = pd.DataFrame({"A": ["x", "y", "z", "z"]}, dtype="category")
            result = ProcessResult(result_df)
            result.truncate_in_place_if_too_big()
            assert_frame_equal(
                result.dataframe, pd.DataFrame({"A": ["x", "y"]}, dtype="category")
            )

    def test_truncate_not_too_big(self):
        df = pd.DataFrame({"foo": ["foo", "bar", "baz"]})
        expected = ProcessResult(df.copy())
        result = ProcessResult(df)
        result.truncate_in_place_if_too_big()

        self.assertEqual(result, expected)

    def test_columns(self):
        df = pd.DataFrame(
            {
                "A": [1],  # number
                "B": ["foo"],  # str
                "C": dt(2018, 8, 20),  # datetime64
            }
        )
        df["D"] = pd.Series(["cat"], dtype="category")
        result = ProcessResult(df)
        self.assertEqual(result.column_names, ["A", "B", "C", "D"])
        self.assertEqual(
            result.columns,
            [
                Column("A", ColumnType.NUMBER()),
                Column("B", ColumnType.TEXT()),
                Column("C", ColumnType.DATETIME()),
                Column("D", ColumnType.TEXT()),
            ],
        )

    def test_empty_columns(self):
        result = ProcessResult()
        self.assertEqual(result.column_names, [])
        self.assertEqual(result.columns, [])

    def test_table_shape(self):
        df = pd.DataFrame({"A": [1, 2, 3]})
        result = ProcessResult(df)
        self.assertEqual(
            result.table_shape, TableShape(3, [Column("A", ColumnType.NUMBER())])
        )

    def test_empty_table_shape(self):
        result = ProcessResult()
        self.assertEqual(result.table_shape, TableShape(0, []))
