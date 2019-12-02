from datetime import datetime as dt
import os
from pathlib import Path
import tempfile
import unittest
import numpy as np
import pandas as pd
from pandas.testing import assert_series_equal, assert_frame_equal
import pyarrow
from cjwkernel.pandas.types import (
    Column,
    ColumnType,
    ProcessResult,
    QuickFix,
    TableShape,
    arrow_table_to_dataframe,
    dataframe_to_arrow_table,
    _coerce_to_i18n_message_dict,
    _coerce_to_process_result_error,
)
import cjwkernel.types as atypes
from cjwkernel.util import create_tempfile
from cjwkernel.tests.util import (
    override_settings,
    arrow_table,
    assert_arrow_table_equals,
)


class ColumnTypeTextTests(unittest.TestCase):
    def test_text_type(self):
        series = pd.Series(["x", np.nan, "z"])
        column_type = ColumnType.TEXT()
        result = column_type.format_series(series)
        assert_series_equal(result, pd.Series(["x", np.nan, "z"]))

    def test_from_arrow(self):
        self.assertEqual(
            ColumnType.from_arrow(atypes.ColumnType.Text()), ColumnType.TEXT()
        )

    def test_to_arrow(self):
        self.assertEqual(ColumnType.TEXT().to_arrow(), atypes.ColumnType.Text())


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

    def test_from_arrow(self):
        self.assertEqual(
            ColumnType.from_arrow(atypes.ColumnType.Number("{:,d}")),
            ColumnType.NUMBER("{:,d}"),
        )

    def test_to_arrow(self):
        self.assertEqual(
            ColumnType.NUMBER("{:,d}").to_arrow(), atypes.ColumnType.Number("{:,d}")
        )


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

    def test_from_arrow(self):
        self.assertEqual(
            ColumnType.from_arrow(atypes.ColumnType.Datetime()), ColumnType.DATETIME()
        )

    def test_to_arrow(self):
        self.assertEqual(ColumnType.DATETIME().to_arrow(), atypes.ColumnType.Datetime())


class ColumnTests(unittest.TestCase):
    def test_from_arrow(self):
        self.assertEqual(
            Column.from_arrow(atypes.Column("A", atypes.ColumnType.Number("{:,d}"))),
            Column("A", ColumnType.NUMBER("{:,d}")),
        )

    def test_to_arrow(self):
        self.assertEqual(
            Column("A", ColumnType.NUMBER("{:,d}")).to_arrow(),
            atypes.Column("A", atypes.ColumnType.Number("{:,d}")),
        )


class TableShapeTests(unittest.TestCase):
    def test_from_arrow(self):
        self.assertEqual(
            TableShape.from_arrow(
                atypes.TableMetadata(
                    3,
                    [
                        atypes.Column("A", atypes.ColumnType.Number("{:,d}")),
                        atypes.Column("B", atypes.ColumnType.Text()),
                    ],
                )
            ),
            TableShape(
                3,
                [
                    Column("A", ColumnType.NUMBER("{:,d}")),
                    Column("B", ColumnType.TEXT()),
                ],
            ),
        )

    def test_to_arrow(self):
        self.assertEqual(
            TableShape(
                3,
                [
                    Column("A", ColumnType.NUMBER("{:,d}")),
                    Column("B", ColumnType.TEXT()),
                ],
            ).to_arrow(),
            atypes.TableMetadata(
                3,
                [
                    atypes.Column("A", atypes.ColumnType.Number("{:,d}")),
                    atypes.Column("B", atypes.ColumnType.Text()),
                ],
            ),
        )


class I18nMessageDictCoercing(unittest.TestCase):
    def test_from_string(self):
        self.assertEqual(
            _coerce_to_i18n_message_dict("some string"),
            atypes.I18nMessage.TODO_i18n("some string").to_dict(),
        )

    def test_from_tuple(self):
        self.assertEqual(
            _coerce_to_i18n_message_dict(("my_id", {"hello": "there"})),
            atypes.I18nMessage("my_id", {"hello": "there"}).to_dict(),
        )

    def test_from_dict(self):
        with self.assertRaises(TypeError):
            _coerce_to_i18n_message_dict(
                {"id": "my_id", "arguments": {"hello": "there"}}
            )


class ProcessResultErrorCoercing(unittest.TestCase):
    def test_from_string(self):
        self.assertEqual(
            _coerce_to_process_result_error("some string"),
            [(atypes.I18nMessage.TODO_i18n("some string").to_dict(), [])],
        )

    def test_from_message_tuple(self):
        self.assertEqual(
            _coerce_to_process_result_error(("my_id", {"hello": "there"})),
            [(atypes.I18nMessage("my_id", {"hello": "there"}).to_dict(), [])],
        )

    def test_from_dict(self):
        with self.assertRaises(ValueError):
            _coerce_to_process_result_error(
                {"id": "my_id", "arguments": {"hello": "there"}}
            )

    def test_from_string_with_quick_fix(self):
        self.assertEqual(
            _coerce_to_process_result_error(
                {
                    "message": "error",
                    "quickFixes": [
                        (
                            "button text",
                            "prependModule",
                            ["converttotext", {"colnames": ["A", "B"]}],
                        )
                    ],
                }
            ),
            [
                (
                    atypes.I18nMessage.TODO_i18n("error").to_dict(),
                    [
                        QuickFix(
                            atypes.I18nMessage.TODO_i18n("button text").to_dict(),
                            "prependModule",
                            [["converttotext", {"colnames": ["A", "B"]}]],
                        )
                    ],
                )
            ],
        )

    def test_from_tuple_with_quick_fixes(self):
        self.assertEqual(
            _coerce_to_process_result_error(
                {
                    "message": ("my id", {}),
                    "quickFixes": [
                        (
                            "button text",
                            "prependModule",
                            ["converttotext", {"colnames": ["A", "B"]}],
                        ),
                        (
                            ("other button text id", {}),
                            "prependModule",
                            ["converttonumber", {"colnames": ["C", "D"]}],
                        ),
                    ],
                }
            ),
            [
                (
                    atypes.I18nMessage("my id", {}).to_dict(),
                    [
                        QuickFix(
                            atypes.I18nMessage.TODO_i18n("button text").to_dict(),
                            "prependModule",
                            [["converttotext", {"colnames": ["A", "B"]}]],
                        ),
                        QuickFix(
                            atypes.I18nMessage("other button text id", {}).to_dict(),
                            "prependModule",
                            [["converttonumber", {"colnames": ["C", "D"]}]],
                        ),
                    ],
                )
            ],
        )

    def test_from_empty_list(self):
        self.assertEqual(_coerce_to_process_result_error([]), [])

    def test_from_list_of_string(self):
        self.assertEqual(
            _coerce_to_process_result_error(["error"]),
            [(atypes.I18nMessage.TODO_i18n("error").to_dict(), [])],
        )

    def test_from_list_of_string_and_tuples(self):
        self.assertEqual(
            _coerce_to_process_result_error(
                ["error", ("my_id", {}), ("my_other_id", {"this": "one"})]
            ),
            [
                (atypes.I18nMessage.TODO_i18n("error").to_dict(), []),
                (atypes.I18nMessage("my_id", {}).to_dict(), []),
                (atypes.I18nMessage("my_other_id", {"this": "one"}).to_dict(), []),
            ],
        )

    def test_from_list_with_quick_fixes(self):
        self.assertEqual(
            _coerce_to_process_result_error(
                [
                    {
                        "message": ("my id", {}),
                        "quickFixes": [
                            (
                                "button text",
                                "prependModule",
                                ["converttotext", {"colnames": ["A", "B"]}],
                            )
                        ],
                    },
                    {
                        "message": ("my other id", {"other": "this"}),
                        "quickFixes": [
                            (
                                ("quick fix id", {"fix": "that"}),
                                "prependModule",
                                ["converttodate", {"colnames": ["C", "D"]}],
                            ),
                            (
                                ("another quick fix id", {"fix": "that"}),
                                "prependModule",
                                ["converttonumber", {"colnames": ["E", "F"]}],
                            ),
                        ],
                    },
                ]
            ),
            [
                (
                    atypes.I18nMessage("my id", {}).to_dict(),
                    [
                        QuickFix(
                            atypes.I18nMessage.TODO_i18n("button text").to_dict(),
                            "prependModule",
                            [["converttotext", {"colnames": ["A", "B"]}]],
                        )
                    ],
                ),
                (
                    atypes.I18nMessage("my other id", {"other": "this"}).to_dict(),
                    [
                        QuickFix(
                            atypes.I18nMessage(
                                "quick fix id", {"fix": "that"}
                            ).to_dict(),
                            "prependModule",
                            [["converttodate", {"colnames": ["C", "D"]}]],
                        ),
                        QuickFix(
                            atypes.I18nMessage(
                                "another quick fix id", {"fix": "that"}
                            ).to_dict(),
                            "prependModule",
                            [["converttonumber", {"colnames": ["E", "F"]}]],
                        ),
                    ],
                ),
            ],
        )

    def test_from_list_of_lists(self):
        with self.assertRaises(ValueError):
            _coerce_to_process_result_error([["hello"]])


class QuickFixTests(unittest.TestCase):
    def test_to_arrow(self):
        self.assertEqual(
            QuickFix(
                atypes.I18nMessage.TODO_i18n("button text").to_dict(),
                "prependModule",
                ["converttotext", {"colnames": ["A", "B"]}],
            ).to_arrow(),
            atypes.QuickFix(
                atypes.I18nMessage.TODO_i18n("button text"),
                atypes.QuickFixAction.PrependStep(
                    "converttotext", {"colnames": ["A", "B"]}
                ),
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
            {"dataframe": table, "column_formats": {"A": "{:,d}"}},
            try_fallback_columns=[Column("A", ColumnType.NUMBER("{:,.2f}"))],
        )
        self.assertEqual(result.columns, [Column("A", ColumnType.NUMBER("{:,d}"))])

    def test_coerce_validate_dataframe(self):
        # Just one test, to ensure validate_dataframe() is used
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
        expected = ProcessResult(errors=_coerce_to_process_result_error("yay"))
        result = ProcessResult.coerce("yay")
        self.assertEqual(result, expected)

    def test_coerce_tuple_dataframe_none(self):
        df = pd.DataFrame({"foo": ["bar"]})
        expected = ProcessResult(dataframe=df)
        result = ProcessResult.coerce((df, None))
        self.assertEqual(result, expected)

    def test_coerce_tuple_dataframe_str(self):
        df = pd.DataFrame({"foo": ["bar"]})
        expected = ProcessResult(
            dataframe=df, errors=_coerce_to_process_result_error("hi")
        )
        result = ProcessResult.coerce((df, "hi"))
        self.assertEqual(result, expected)

    def test_coerce_tuple_dataframe_internationalized(self):
        df = pd.DataFrame({"foo": ["bar"]})
        expected = ProcessResult(
            dataframe=df,
            errors=_coerce_to_process_result_error(("message.id", {"param1": "a"})),
        )
        result = ProcessResult.coerce((df, ("message.id", {"param1": "a"})))
        self.assertEqual(result, expected)

    def test_coerce_tuple_none_str(self):
        expected = ProcessResult(errors=_coerce_to_process_result_error("hi"))
        result = ProcessResult.coerce((None, "hi"))
        self.assertEqual(result, expected)

    def test_coerce_tuple_none_internationalized(self):
        expected = ProcessResult(
            errors=_coerce_to_process_result_error(("message.id", {"param1": "a"}))
        )
        result = ProcessResult.coerce((None, ("message.id", {"param1": "a"})))
        self.assertEqual(result, expected)

    def test_coerce_tuple_dataframe_str_dict(self):
        df = pd.DataFrame({"foo": ["bar"]})
        expected = ProcessResult(
            df, _coerce_to_process_result_error("hi"), json={"a": "b"}
        )
        result = ProcessResult.coerce((df, "hi", {"a": "b"}))
        self.assertEqual(result, expected)

    def test_coerce_tuple_dataframe_internationalized_dict(self):
        df = pd.DataFrame({"foo": ["bar"]})
        expected = ProcessResult(
            df,
            _coerce_to_process_result_error(("message.id", {"param1": "a"})),
            json={"a": "b"},
        )
        result = ProcessResult.coerce((df, ("message.id", {"param1": "a"}), {"a": "b"}))
        self.assertEqual(result, expected)

    def test_coerce_tuple_dataframe_str_none(self):
        df = pd.DataFrame({"foo": ["bar"]})
        expected = ProcessResult(df, _coerce_to_process_result_error("hi"))
        result = ProcessResult.coerce((df, "hi", None))
        self.assertEqual(result, expected)

    def test_coerce_tuple_dataframe_internationalized_none(self):
        df = pd.DataFrame({"foo": ["bar"]})
        expected = ProcessResult(
            df, _coerce_to_process_result_error(("message.id", {"param1": "a"}))
        )
        result = ProcessResult.coerce((df, ("message.id", {"param1": "a"}), None))
        self.assertEqual(result, expected)

    def test_coerce_tuple_dataframe_none_dict(self):
        df = pd.DataFrame({"foo": ["bar"]})
        expected = ProcessResult(df, [], json={"a": "b"})
        result = ProcessResult.coerce((df, None, {"a": "b"}))
        self.assertEqual(result, expected)

    def test_coerce_tuple_dataframe_none_none(self):
        df = pd.DataFrame({"foo": ["bar"]})
        expected = ProcessResult(df)
        result = ProcessResult.coerce((df, None, None))
        self.assertEqual(result, expected)

    def test_coerce_tuple_none_str_dict(self):
        expected = ProcessResult(
            errors=_coerce_to_process_result_error("hi"), json={"a": "b"}
        )
        result = ProcessResult.coerce((None, "hi", {"a": "b"}))
        self.assertEqual(result, expected)

    def test_coerce_tuple_none_internationalized_dict(self):
        expected = ProcessResult(
            errors=_coerce_to_process_result_error(("message.id", {"param1": "a"})),
            json={"a": "b"},
        )
        result = ProcessResult.coerce(
            (None, ("message.id", {"param1": "a"}), {"a": "b"})
        )
        self.assertEqual(result, expected)

    def test_coerce_tuple_none_str_none(self):
        expected = ProcessResult(errors=_coerce_to_process_result_error("hi"))
        result = ProcessResult.coerce((None, "hi", None))
        self.assertEqual(result, expected)

    def test_coerce_tuple_none_internationalized_none(self):
        expected = ProcessResult(
            errors=_coerce_to_process_result_error(("message.id", {"param1": "a"}))
        )
        result = ProcessResult.coerce((None, ("message.id", {"param1": "a"}), None))
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
        self.assertIsNotNone(result.errors)
        self.assertTrue(result.errors)

    def test_coerce_2tuple_no_dataframe(self):
        result = ProcessResult.coerce(("foo", "bar"))
        self.assertIsNotNone(result.errors)
        self.assertTrue(result.errors)

    def test_coerce_2tuple_internationalized(self):
        expected = ProcessResult(
            errors=_coerce_to_process_result_error(("message_id", {"param1": "a"}))
        )
        result = ProcessResult.coerce(("message_id", {"param1": "a"}))
        self.assertEqual(result, expected)

    def test_coerce_2tuple_bad_internationalized_error(self):
        result = ProcessResult.coerce(("message_id", None))
        self.assertIsNotNone(result.errors)
        self.assertTrue(result.errors)

    def test_coerce_3tuple_no_dataframe(self):
        result = ProcessResult.coerce(("foo", "bar", {"a": "b"}))
        self.assertIsNotNone(result.errors)
        self.assertTrue(result.errors)

    def test_coerce_dict_internationalized(self):
        expected = ProcessResult(
            errors=[
                (
                    atypes.I18nMessage.TODO_i18n("an error").to_dict(),
                    [
                        QuickFix(
                            atypes.I18nMessage("message.id", {}).to_dict(),
                            "prependModule",
                            ["texttodate", {"column": "created_at"}],
                        )
                    ],
                )
            ]
        )
        result = ProcessResult.coerce(
            {
                "message": "an error",
                "quickFixes": [
                    (
                        ("message.id", {}),
                        "prependModule",
                        "texttodate",
                        {"column": "created_at"},
                    )
                ],
            }
        )
        self.assertEqual(result, expected)

    def test_coerce_dict_legacy_with_quickfix_tuple(self):
        dataframe = pd.DataFrame({"A": [1, 2]})
        quick_fix = QuickFix(
            atypes.I18nMessage.TODO_i18n("Hi").to_dict(),
            "prependModule",
            ["texttodate", {"column": "created_at"}],
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
            dataframe,
            [(atypes.I18nMessage.TODO_i18n("an error").to_dict(), [quick_fix])],
            json={"foo": "bar"},
        )
        self.assertEqual(result, expected)

    def test_coerce_dict_with_quickfix_tuple(self):
        dataframe = pd.DataFrame({"A": [1, 2]})
        quick_fix = QuickFix(
            atypes.I18nMessage("message.id", {}).to_dict(),
            "prependModule",
            ["texttodate", {"column": "created_at"}],
        )
        result = ProcessResult.coerce(
            {
                "dataframe": dataframe,
                "errors": [
                    {
                        "message": "an error",
                        "quickFixes": [
                            (
                                ("message.id", {}),
                                "prependModule",
                                "texttodate",
                                {"column": "created_at"},
                            )
                        ],
                    }
                ],
                "json": {"foo": "bar"},
            }
        )
        expected = ProcessResult(
            dataframe,
            [(atypes.I18nMessage.TODO_i18n("an error").to_dict(), [quick_fix])],
            json={"foo": "bar"},
        )
        self.assertEqual(result, expected)

    def test_coerce_dict_legacy_with_quickfix_tuple_not_json_serializable(self):
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

    def test_coerce_dict_with_quickfix_tuple_not_json_serializable(self):
        dataframe = pd.DataFrame({"A": [1, 2]})
        with self.assertRaisesRegex(ValueError, "cannot be coerced"):
            ProcessResult.coerce(
                {
                    "dataframe": dataframe,
                    "errors": [
                        {
                            "message": "an error",
                            "quickFixes": [
                                (
                                    "Hi",
                                    "prependModule",
                                    "texttodate",
                                    {"columns": pd.Index(["created_at"])},
                                )
                            ],
                        }
                    ],
                    "json": {"foo": "bar"},
                }
            )

    def test_coerce_dict_legacy_with_quickfix_dict(self):
        dataframe = pd.DataFrame({"A": [1, 2]})
        quick_fix = QuickFix(
            atypes.I18nMessage.TODO_i18n("Hi").to_dict(),
            "prependModule",
            ["texttodate", {"column": "created_at"}],
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
            dataframe,
            errors=[(atypes.I18nMessage.TODO_i18n("an error").to_dict(), [quick_fix])],
            json={"foo": "bar"},
        )
        self.assertEqual(result, expected)

    def test_coerce_dict_with_quickfix_dict(self):
        dataframe = pd.DataFrame({"A": [1, 2]})
        quick_fix = QuickFix(
            atypes.I18nMessage.TODO_i18n("Hi").to_dict(),
            "prependModule",
            ["texttodate", {"column": "created_at"}],
        )
        result = ProcessResult.coerce(
            {
                "dataframe": dataframe,
                "errors": [
                    {
                        "message": "an error",
                        "quickFixes": [
                            {
                                "text": "Hi",
                                "action": "prependModule",
                                "args": ["texttodate", {"column": "created_at"}],
                            }
                        ],
                    }
                ],
                "json": {"foo": "bar"},
            }
        )
        expected = ProcessResult(
            dataframe,
            errors=[(atypes.I18nMessage.TODO_i18n("an error").to_dict(), [quick_fix])],
            json={"foo": "bar"},
        )
        self.assertEqual(result, expected)

    def test_coerce_dict_quickfix_multiple(self):
        dataframe = pd.DataFrame({"A": [1, 2]})
        quick_fixes = [
            QuickFix(
                atypes.I18nMessage.TODO_i18n("Hi").to_dict(),
                "prependModule",
                ["texttodate", {"column": "created_at"}],
            ),
            QuickFix(
                atypes.I18nMessage("message.id", {}).to_dict(),
                "prependModule",
                ["texttodate", {"column": "created_at"}],
            ),
        ]
        result = ProcessResult.coerce(
            {
                "dataframe": dataframe,
                "errors": [
                    {
                        "message": "an error",
                        "quickFixes": [
                            {
                                "text": "Hi",
                                "action": "prependModule",
                                "args": ["texttodate", {"column": "created_at"}],
                            },
                            (
                                ("message.id", {}),
                                "prependModule",
                                "texttodate",
                                {"column": "created_at"},
                            ),
                        ],
                    },
                    "other error",
                ],
                "json": {"foo": "bar"},
            }
        )
        expected = ProcessResult(
            dataframe,
            errors=[
                (atypes.I18nMessage.TODO_i18n("an error").to_dict(), quick_fixes),
                (atypes.I18nMessage.TODO_i18n("other error").to_dict(), []),
            ],
            json={"foo": "bar"},
        )
        self.assertEqual(result, expected)

    def test_coerce_dict_legacy_bad_quickfix_dict(self):
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

    def test_coerce_dict_bad_quickfix_dict(self):
        with self.assertRaises(ValueError):
            ProcessResult.coerce(
                {
                    "errors": [
                        {
                            "message": "an error",
                            "quickFixes": [
                                {
                                    "text": "Hi",
                                    "action": "prependModule",
                                    "arguments": [
                                        "texttodate",
                                        {"column": "created_at"},
                                    ],
                                }
                            ],
                        }
                    ]
                }
            )

    def test_coerce_dict_legacy_quickfix_dict_has_class_not_json(self):
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

    def test_coerce_dict_quickfix_dict_has_class_not_json(self):
        with self.assertRaisesRegex(ValueError, "cannot be coerced"):
            ProcessResult.coerce(
                {
                    "errors": [
                        {
                            "message": "an error",
                            "quickFixes": [
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
                    ]
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
        self.assertIsNotNone(result.errors)
        self.assertTrue(result.errors)

    def test_status_ok(self):
        result = ProcessResult(pd.DataFrame({"A": [1]}), [])
        self.assertEqual(result.status, "ok")

    def test_status_ok_with_warning(self):
        result = ProcessResult(pd.DataFrame({"A": [1]}), "warning")
        self.assertEqual(result.status, "ok")

    def test_status_ok_with_no_rows(self):
        result = ProcessResult(pd.DataFrame({"A": []}), [])
        self.assertEqual(result.status, "ok")

    def test_status_error(self):
        result = ProcessResult(pd.DataFrame(), "error")
        self.assertEqual(result.status, "error")

    def test_status_unreachable(self):
        result = ProcessResult(pd.DataFrame(), [])
        self.assertEqual(result.status, "unreachable")

    @override_settings(MAX_ROWS_PER_TABLE=2)
    def test_truncate_too_big_no_error(self):
        expected_df = pd.DataFrame({"foo": ["bar", "baz"]})
        expected = ProcessResult(
            dataframe=expected_df,
            errors=[
                (
                    atypes.I18nMessage.TODO_i18n(
                        "Truncated output from 3 rows to 2"
                    ).to_dict(),
                    [],
                )
            ],
        )

        result_df = pd.DataFrame({"foo": ["bar", "baz", "moo"]})
        result = ProcessResult(result_df, errors=[])
        result.truncate_in_place_if_too_big()

        self.assertEqual(result, expected)

    @override_settings(MAX_ROWS_PER_TABLE=2)
    def test_truncate_too_big_and_error(self):
        expected_df = pd.DataFrame({"foo": ["bar", "baz"]})
        expected = ProcessResult(
            dataframe=expected_df,
            errors=[
                (atypes.I18nMessage.TODO_i18n("Some error").to_dict(), []),
                (
                    atypes.I18nMessage.TODO_i18n(
                        "Truncated output from 3 rows to 2"
                    ).to_dict(),
                    [],
                ),
            ],
        )

        result_df = pd.DataFrame({"foo": ["bar", "baz", "moo"]})
        result = ProcessResult(
            result_df,
            errors=[(atypes.I18nMessage.TODO_i18n("Some error").to_dict(), [])],
        )
        result.truncate_in_place_if_too_big()

        self.assertEqual(result, expected)

    @override_settings(MAX_ROWS_PER_TABLE=2)
    def test_truncate_too_big_remove_unused_categories(self):
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

    def test_to_arrow_empty_dataframe(self):
        fd, filename = tempfile.mkstemp()
        os.close(fd)
        # Remove the file. Then we'll test that ProcessResult.to_arrow() does
        # not write it (because the result is an error)
        os.unlink(filename)
        try:
            result = ProcessResult.coerce("bad, bad error").to_arrow(Path(filename))
            self.assertEqual(
                result,
                atypes.RenderResult(
                    atypes.ArrowTable(None, atypes.TableMetadata(0, [])),
                    [
                        atypes.RenderError(
                            atypes.I18nMessage.TODO_i18n("bad, bad error"), []
                        )
                    ],
                    {},
                ),
            )
            with self.assertRaises(FileNotFoundError):
                open(filename)
        finally:
            try:
                os.unlink(filename)
            except FileNotFoundError:
                pass

    def test_to_arrow_quick_fixes(self):
        fd, filename = tempfile.mkstemp()
        os.close(fd)
        # Remove the file. Then we'll test that ProcessResult.to_arrow() does
        # not write it (because the result is an error)
        os.unlink(filename)
        try:
            result = ProcessResult(
                errors=[
                    (
                        atypes.I18nMessage.TODO_i18n("bad, bad error").to_dict(),
                        [
                            QuickFix(
                                atypes.I18nMessage.TODO_i18n("button foo").to_dict(),
                                "prependModule",
                                ["converttotext", {"colnames": ["A", "B"]}],
                            ),
                            QuickFix(
                                atypes.I18nMessage.TODO_i18n("button bar").to_dict(),
                                "prependModule",
                                ["converttonumber", {"colnames": ["A", "B"]}],
                            ),
                        ],
                    )
                ]
            ).to_arrow(Path(filename))
            self.assertEqual(
                result.errors,
                [
                    atypes.RenderError(
                        atypes.I18nMessage.TODO_i18n("bad, bad error"),
                        [
                            atypes.QuickFix(
                                atypes.I18nMessage.TODO_i18n("button foo"),
                                atypes.QuickFixAction.PrependStep(
                                    "converttotext", {"colnames": ["A", "B"]}
                                ),
                            ),
                            atypes.QuickFix(
                                atypes.I18nMessage.TODO_i18n("button bar"),
                                atypes.QuickFixAction.PrependStep(
                                    "converttonumber", {"colnames": ["A", "B"]}
                                ),
                            ),
                        ],
                    )
                ],
            )
            with self.assertRaises(FileNotFoundError):
                open(filename)
        finally:
            try:
                os.unlink(filename)
            except FileNotFoundError:
                pass

    def test_to_arrow_normal_dataframe(self):
        fd, filename = tempfile.mkstemp()
        os.close(fd)
        # Remove the file. Then we'll test that ProcessResult.to_arrow() does
        # not write it (because the result is an error)
        os.unlink(filename)
        try:
            process_result = ProcessResult.coerce(pd.DataFrame({"A": [1, 2]}))
            result = process_result.to_arrow(Path(filename))
            self.assertEqual(
                result,
                atypes.RenderResult(
                    atypes.ArrowTable(
                        Path(filename),
                        atypes.TableMetadata(
                            2,
                            [
                                atypes.Column(
                                    "A",
                                    atypes.ColumnType.Number(
                                        # Whatever .format
                                        # ProcessResult.coerce() gave
                                        process_result.columns[0].type.format
                                    ),
                                )
                            ],
                        ),
                    ),
                    [],
                    {},
                ),
            )
            arrow_table = result.table.table
            self.assertEqual(arrow_table.to_pydict(), {"A": [1, 2]})
        finally:
            os.unlink(filename)


class ArrowConversionTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.path = create_tempfile()

    def tearDown(self):
        self.path.unlink()
        super().tearDown()

    def test_dataframe_all_null_text_column(self):
        assert_arrow_table_equals(
            dataframe_to_arrow_table(
                pd.DataFrame({"A": [None]}, dtype=str),
                [Column("A", ColumnType.TEXT())],
                self.path,
            ),
            arrow_table({"A": pyarrow.array([None], pyarrow.string())}),
        )

    def test_arrow_all_null_text_column(self):
        dataframe, columns = arrow_table_to_dataframe(
            arrow_table(
                {"A": pyarrow.array(["a", "b", None, "c"])},
                columns=[atypes.Column("A", atypes.ColumnType.Text())],
            )
        )
        assert_frame_equal(dataframe, pd.DataFrame({"A": ["a", "b", np.nan, "c"]}))
        self.assertEqual(columns, [Column("A", ColumnType.TEXT())])

    def test_dataframe_category_column(self):
        assert_arrow_table_equals(
            dataframe_to_arrow_table(
                pd.DataFrame({"A": ["A", "B", None, "A"]}, dtype="category"),
                [Column("A", ColumnType.TEXT())],
                self.path,
            ),
            arrow_table(
                {
                    "A": pyarrow.DictionaryArray.from_arrays(
                        pyarrow.array([0, 1, None, 0], type=pyarrow.int8()),
                        pyarrow.array(["A", "B"], type=pyarrow.string()),
                    )
                }
            ),
        )

    def test_arrow_category_column(self):
        atable = arrow_table(
            {
                "A": pyarrow.DictionaryArray.from_arrays(
                    pyarrow.array([0, 1, None, 0], type=pyarrow.int8()),
                    pyarrow.array(["A", "B"], type=pyarrow.string()),
                )
            }
        )
        dataframe, columns = arrow_table_to_dataframe(atable)
        self.assertEqual(columns, [Column("A", ColumnType.TEXT())])
        assert_frame_equal(
            dataframe, pd.DataFrame({"A": ["A", "B", None, "A"]}, dtype="category")
        )

    def test_dataframe_all_null_category_column(self):
        assert_arrow_table_equals(
            dataframe_to_arrow_table(
                pd.DataFrame({"A": [None]}, dtype=str).astype("category"),
                [Column("A", ColumnType.TEXT())],
                self.path,
            ),
            arrow_table(
                {
                    "A": pyarrow.DictionaryArray.from_arrays(
                        pyarrow.array([None], type=pyarrow.int8()),
                        pyarrow.array([], type=pyarrow.string()),
                    )
                }
            ),
        )

    def test_arrow_all_null_category_column(self):
        atable = arrow_table(
            {
                "A": pyarrow.DictionaryArray.from_arrays(
                    pyarrow.array([None], type=pyarrow.int8()),
                    pyarrow.array([], type=pyarrow.string()),
                )
            }
        )
        dataframe, columns = arrow_table_to_dataframe(atable)
        self.assertEqual(columns, [Column("A", ColumnType.TEXT())])
        assert_frame_equal(
            dataframe, pd.DataFrame({"A": [None]}, dtype=str).astype("category")
        )

    def test_dataframe_uint8_column(self):
        assert_arrow_table_equals(
            dataframe_to_arrow_table(
                pd.DataFrame({"A": [1, 2, 3, 253]}, dtype=np.uint8),
                [Column("A", ColumnType.NUMBER("{:,d}"))],
                self.path,
            ),
            arrow_table(
                {"A": pyarrow.array([1, 2, 3, 253], type=pyarrow.uint8())},
                [atypes.Column("A", atypes.ColumnType.Number("{:,d}"))],
            ),
        )

    def test_arrow_uint8_column(self):
        dataframe, columns = arrow_table_to_dataframe(
            arrow_table(
                {"A": pyarrow.array([1, 2, 3, 253], type=pyarrow.uint8())},
                columns=[atypes.Column("A", atypes.ColumnType.Number("{:,d}"))],
            )
        )
        assert_frame_equal(
            dataframe, pd.DataFrame({"A": [1, 2, 3, 253]}, dtype=np.uint8)
        )
        self.assertEqual(columns, [Column("A", ColumnType.NUMBER("{:,d}"))])

    def test_dataframe_datetime_column(self):
        assert_arrow_table_equals(
            dataframe_to_arrow_table(
                pd.DataFrame(
                    {"A": ["2019-09-17T21:21:00.123456Z", None]}, dtype="datetime64[ns]"
                ),
                [Column("A", ColumnType.DATETIME())],
                self.path,
            ),
            arrow_table(
                {
                    "A": pyarrow.array(
                        [dt.fromisoformat("2019-09-17T21:21:00.123456"), None],
                        type=pyarrow.timestamp(unit="ns", tz=None),
                    )
                },
                [atypes.Column("A", atypes.ColumnType.Datetime())],
            ),
        )

    def test_arrow_datetime_column(self):
        dataframe, columns = arrow_table_to_dataframe(
            arrow_table(
                {
                    "A": pyarrow.array(
                        [dt.fromisoformat("2019-09-17T21:21:00.123456"), None],
                        type=pyarrow.timestamp(unit="ns", tz=None),
                    )
                },
                [atypes.Column("A", atypes.ColumnType.Datetime())],
            )
        )
        assert_frame_equal(
            dataframe,
            pd.DataFrame(
                {"A": ["2019-09-17T21:21:00.123456Z", None]}, dtype="datetime64[ns]"
            ),
        )
        self.assertEqual(columns, [Column("A", ColumnType.DATETIME())])

    def test_arrow_table_reuse_string_memory(self):
        dataframe, _ = arrow_table_to_dataframe(arrow_table({"A": ["x", "x"]}))
        self.assertIs(dataframe["A"][0], dataframe["A"][1])
