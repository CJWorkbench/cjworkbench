import os
import tempfile
import unittest
from datetime import datetime as dt
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
import pyarrow as pa
from pandas.testing import assert_frame_equal
from cjwmodule.arrow.testing import make_table, make_column, assert_arrow_table_equals

import cjwkernel.types as atypes
from cjwkernel.i18n import TODO_i18n
from cjwkernel.pandas.types import (
    Column,
    ColumnType,
    ProcessResult,
    RenderColumn,
    RenderError,
    QuickFix,
    QuickFixAction,
    coerce_I18nMessage,
    coerce_RenderError_list,
    coerce_RenderError,
    dataframe_to_arrow_table,
    arrow_schema_to_render_columns,
)
from cjwkernel.tests.util import override_settings, tempfile_context
from cjwkernel.util import create_tempfile
from cjwkernel.validate import load_untrusted_arrow_file_with_columns
from cjwmodule.i18n import I18nMessage


class I18nMessageTests(unittest.TestCase):
    def test_coerce_from_string(self):
        self.assertEqual(
            coerce_I18nMessage("some string"),
            I18nMessage("TODO_i18n", {"text": "some string"}, None),
        )

    def test_coerce_from_tuple(self):
        self.assertEqual(
            coerce_I18nMessage(("my_id", {"hello": "there"})),
            I18nMessage("my_id", {"hello": "there"}, None),
        )

    def test_coerce_from_dict(self):
        with self.assertRaises(ValueError):
            coerce_I18nMessage({"id": "my_id", "arguments": {"hello": "there"}})

    def test_coerce_with_source_none(self):
        self.assertEqual(
            coerce_I18nMessage(("my_id", {"hello": "there"}, None)),
            I18nMessage("my_id", {"hello": "there"}, None),
        )

    def test_coerce_with_source_empty(self):
        with self.assertRaises(ValueError):
            coerce_I18nMessage(("my_id", {"hello": "there"}, {})),

    def test_coerce_with_source_module(self):
        self.assertEqual(
            coerce_I18nMessage(("my_id", {"hello": "there"}, "module")),
            I18nMessage("my_id", {"hello": "there"}, "module"),
        )

    def test_coerce_with_source_library(self):
        self.assertEqual(
            coerce_I18nMessage(("my_id", {"hello": "there"}, "cjwmodule")),
            I18nMessage("my_id", {"hello": "there"}, "cjwmodule"),
        )

    def test_coerce_with_source_library_none(self):
        self.assertEqual(
            coerce_I18nMessage(("my_id", {"hello": "there"}, None)),
            I18nMessage("my_id", {"hello": "there"}, None),
        )

    def test_coerce_with_source_error_type_dict(self):
        with self.assertRaises(ValueError):
            coerce_I18nMessage(("my_id", {"hello": "there"}, {"library": "cjwmodule"}))

    def test_coerce_with_invalid_source(self):
        with self.assertRaises(ValueError):
            coerce_I18nMessage(("my_id", {"hello": "there"}, "random"))


class RenderErrorTests(unittest.TestCase):
    def test_from_string(self):
        self.assertEqual(
            coerce_RenderError("some string"),
            RenderError(I18nMessage("TODO_i18n", {"text": "some string"}, None)),
        )

    def test_from_none(self):
        with self.assertRaises(ValueError):
            coerce_RenderError(None)

    def test_from_message_2tuple(self):
        self.assertEqual(
            coerce_RenderError(("my_id", {"hello": "there"})),
            RenderError(I18nMessage("my_id", {"hello": "there"}, None)),
        )

    def test_from_message_3tuple(self):
        self.assertEqual(
            coerce_RenderError(("my_id", {"hello": "there"}, "cjwmodule")),
            RenderError(I18nMessage("my_id", {"hello": "there"}, "cjwmodule")),
        )

    def test_from_dict_without_message(self):
        with self.assertRaises(ValueError):
            coerce_RenderError({"id": "my_id", "arguments": {"hello": "there"}})

    def test_from_dict_without_quick_fixes(self):
        self.assertEqual(
            coerce_RenderError({"message": ("my id", {})}),
            RenderError(I18nMessage("my id", {}, None), []),
        )

    def test_from_string_with_quick_fix(self):
        self.assertEqual(
            coerce_RenderError(
                {
                    "message": "error",
                    "quickFixes": [
                        dict(
                            text="button text",
                            action="prependModule",
                            args=["converttotext", {"colnames": ["A", "B"]}],
                        )
                    ],
                }
            ),
            RenderError(
                TODO_i18n("error"),
                [
                    QuickFix(
                        TODO_i18n("button text"),
                        QuickFixAction.PrependStep(
                            "converttotext", {"colnames": ["A", "B"]}
                        ),
                    )
                ],
            ),
        )

    def test_from_list(self):
        with self.assertRaises(ValueError):
            coerce_RenderError([{"id": "my_id", "arguments": {"hello": "there"}}])

    def test_list_from_empty_list(self):
        self.assertEqual(coerce_RenderError_list([]), [])

    def test_list_from_list_of_string(self):
        self.assertEqual(
            coerce_RenderError_list(["error"]),
            [RenderError(TODO_i18n("error"))],
        )

    def test_list_from_list_of_string_and_tuples(self):
        self.assertEqual(
            coerce_RenderError_list(
                ["error", ("my_id", {}), ("my_other_id", {"this": "one"})]
            ),
            [
                RenderError(TODO_i18n("error")),
                RenderError(I18nMessage("my_id", {}, None)),
                RenderError(I18nMessage("my_other_id", {"this": "one"}, None)),
            ],
        )

    def test_list_from_list_with_quick_fixes(self):
        self.assertEqual(
            coerce_RenderError_list(
                [
                    {
                        "message": ("my id", {}),
                        "quickFixes": [
                            dict(
                                text="button text",
                                action="prependModule",
                                args=["converttotext", {"colnames": ["A", "B"]}],
                            )
                        ],
                    },
                    {
                        "message": ("my other id", {"other": "this"}),
                        "quickFixes": [
                            dict(
                                text=("quick fix id", {"fix": "that"}),
                                action="prependModule",
                                args=["convert-date", {"colnames": ["C", "D"]}],
                            ),
                            dict(
                                text=("another quick fix id", {"fix": "that"}),
                                action="prependModule",
                                args=["converttonumber", {"colnames": ["E", "F"]}],
                            ),
                        ],
                    },
                ]
            ),
            [
                RenderError(
                    I18nMessage("my id", {}, None),
                    [
                        QuickFix(
                            TODO_i18n("button text"),
                            QuickFixAction.PrependStep(
                                "converttotext", {"colnames": ["A", "B"]}
                            ),
                        )
                    ],
                ),
                RenderError(
                    I18nMessage("my other id", {"other": "this"}, None),
                    [
                        QuickFix(
                            I18nMessage("quick fix id", {"fix": "that"}, None),
                            QuickFixAction.PrependStep(
                                "convert-date", {"colnames": ["C", "D"]}
                            ),
                        ),
                        QuickFix(
                            I18nMessage("another quick fix id", {"fix": "that"}, None),
                            QuickFixAction.PrependStep(
                                "converttonumber", {"colnames": ["E", "F"]}
                            ),
                        ),
                    ],
                ),
            ],
        )

    def test_list_from_list_of_lists(self):
        with self.assertRaises(ValueError):
            coerce_RenderError_list([["hello"]])

    def test_list_from_none(self):
        self.assertEqual(coerce_RenderError_list(None), [])

    def test_list_from_empty_string(self):
        self.assertEqual(coerce_RenderError_list(""), [])

    def test_list_from_nonempty_string(self):
        result = coerce_RenderError_list("hello")
        expected = [RenderError(TODO_i18n("hello"))]
        self.assertEqual(result, expected)

    def test_list_from_tuple(self):
        result = coerce_RenderError_list(("id", {"arg": "1"}))
        expected = [RenderError(I18nMessage("id", {"arg": "1"}, None))]
        self.assertEqual(result, expected)

    def test_list_from_dict(self):
        result = coerce_RenderError_list({"message": "error", "quickFixes": []})
        expected = [RenderError(TODO_i18n("error"))]
        self.assertEqual(result, expected)


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
                    "D": [pd.Period("2021-01-01", freq="D"), pd.NaT],
                }
            )
        )
        self.assertEqual(
            result.columns,
            [
                Column("A", ColumnType.Number()),
                Column("B", ColumnType.Text()),
                Column("C", ColumnType.Timestamp()),
                Column("D", ColumnType.Date("day")),
            ],
        )

    def test_coerce_infer_columns(self):
        table = pd.DataFrame({"A": [1, 2], "B": ["x", "y"]})
        result = ProcessResult.coerce(table)
        self.assertEqual(
            result.columns,
            [Column("A", ColumnType.Number()), Column("B", ColumnType.Text())],
        )

    def test_coerce_infer_columns_with_format(self):
        table = pd.DataFrame({"A": [1, 2], "B": ["x", "y"]})
        result = ProcessResult.coerce(
            {"dataframe": table, "column_formats": {"A": "{:,d}"}}
        )
        self.assertEqual(
            result.columns,
            [
                Column("A", ColumnType.Number(format="{:,d}")),
                Column("B", ColumnType.Text()),
            ],
        )

    def test_coerce_infer_columns_with_unit(self):
        table = pd.DataFrame(
            {"A": [pd.Period("2021-01-01", freq="D"), None], "B": ["x", "y"]}
        )
        result = ProcessResult.coerce(
            {"dataframe": table, "column_formats": {"A": "year"}}
        )
        self.assertEqual(
            result.columns,
            [
                Column("A", ColumnType.Date(unit="year")),
                Column("B", ColumnType.Text()),
            ],
        )

    def test_coerce_infer_columns_invalid_format_is_error(self):
        table = pd.DataFrame({"A": [1, 2]})
        with self.assertRaisesRegex(ValueError, 'Format must look like "{:...}"'):
            ProcessResult.coerce({"dataframe": table, "column_formats": {"A": "day"}})

    def test_coerce_infer_columns_invalid_unit_is_error(self):
        table = pd.DataFrame({"A": [pd.Period("2021-01-01", freq="D")]})
        with self.assertRaisesRegex(
            ValueError, 'Unit must be "day", "week", "month", "quarter" or "year"'
        ):
            ProcessResult.coerce({"dataframe": table, "column_formats": {"A": "{,g}"}})

    def test_coerce_infer_columns_wrong_type_format_is_error(self):
        table = pd.DataFrame({"A": [1, 2]})
        with self.assertRaisesRegex(TypeError, "Format must be str"):
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
                Column("A", ColumnType.Number("{:,d}")),
                Column("B", ColumnType.Text()),
            ],
        )
        self.assertEqual(
            result.columns,
            [Column("A", ColumnType.Number("{:,d}")), Column("B", ColumnType.Text())],
        )

    def test_coerce_infer_columns_try_fallback_columns_ignore_wrong_type(self):
        table = pd.DataFrame({"A": [1, 2], "B": ["x", "y"]})
        result = ProcessResult.coerce(
            table,
            try_fallback_columns=[
                Column("A", ColumnType.Text()),
                Column("B", ColumnType.Number()),
            ],
        )
        self.assertEqual(
            result.columns,
            [Column("A", ColumnType.Number()), Column("B", ColumnType.Text())],
        )

    def test_coerce_infer_columns_format_supercedes_try_fallback_columns(self):
        table = pd.DataFrame({"A": [1, 2]})
        result = ProcessResult.coerce(
            {"dataframe": table, "column_formats": {"A": "{:,d}"}},
            try_fallback_columns=[Column("A", ColumnType.Number("{:,.2f}"))],
        )
        self.assertEqual(result.columns, [Column("A", ColumnType.Number("{:,d}"))])

    def test_coerce_validate_dataframe(self):
        # Just one test, to ensure validate_dataframe() is used
        with self.assertRaisesRegex(ValueError, "must use the default RangeIndex"):
            ProcessResult.coerce(pd.DataFrame({"A": [1, 2]})[1:])

    def test_coerce_validate_processresult(self):
        # ProcessResult.coerce(<ProcessResult>) should raise on error.

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
        # ValueError on ProcessResult.coerce(<ProcessResult>).
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
        expected = ProcessResult(errors=[RenderError(TODO_i18n("yay"))])
        result = ProcessResult.coerce("yay")
        self.assertEqual(result, expected)

    def test_coerce_tuple_dataframe_none(self):
        df = pd.DataFrame({"foo": ["bar"]})
        expected = ProcessResult(dataframe=df)
        result = ProcessResult.coerce((df, None))
        self.assertEqual(result, expected)

    def test_coerce_tuple_dataframe_str(self):
        df = pd.DataFrame({"foo": ["bar"]})
        expected = ProcessResult(dataframe=df, errors=[RenderError(TODO_i18n("hi"))])
        result = ProcessResult.coerce((df, "hi"))
        self.assertEqual(result, expected)

    def test_coerce_tuple_dataframe_i18n(self):
        df = pd.DataFrame({"foo": ["bar"]})
        expected = ProcessResult(
            dataframe=df,
            errors=[RenderError(I18nMessage("message.id", {"param1": "a"}, None))],
        )
        result = ProcessResult.coerce((df, ("message.id", {"param1": "a"})))
        self.assertEqual(result, expected)

    def test_coerce_tuple_none_str(self):
        expected = ProcessResult(errors=[RenderError(TODO_i18n("hi"))])
        result = ProcessResult.coerce((None, "hi"))
        self.assertEqual(result, expected)

    def test_coerce_tuple_none_i18n(self):
        expected = ProcessResult(
            errors=[RenderError(I18nMessage("message.id", {"param1": "a"}, None))]
        )
        result = ProcessResult.coerce((None, ("message.id", {"param1": "a"})))
        self.assertEqual(result, expected)

    def test_coerce_tuple_dataframe_str_dict(self):
        df = pd.DataFrame({"foo": ["bar"]})
        expected = ProcessResult(df, [RenderError(TODO_i18n("hi"))], json={"a": "b"})
        result = ProcessResult.coerce((df, "hi", {"a": "b"}))
        self.assertEqual(result, expected)

    def test_coerce_tuple_dataframe_i18n_dict(self):
        df = pd.DataFrame({"foo": ["bar"]})
        expected = ProcessResult(
            df,
            [RenderError(I18nMessage("message.id", {"param1": "a"}, None))],
            json={"a": "b"},
        )
        result = ProcessResult.coerce((df, ("message.id", {"param1": "a"}), {"a": "b"}))
        self.assertEqual(result, expected)

    def test_coerce_tuple_dataframe_str_none(self):
        df = pd.DataFrame({"foo": ["bar"]})
        expected = ProcessResult(df, [RenderError(TODO_i18n("hi"))])
        result = ProcessResult.coerce((df, "hi", None))
        self.assertEqual(result, expected)

    def test_coerce_tuple_dataframe_i18n_none(self):
        df = pd.DataFrame({"foo": ["bar"]})
        expected = ProcessResult(
            df, [RenderError(I18nMessage("message.id", {"param1": "a"}, None))]
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
        expected = ProcessResult(errors=[RenderError(TODO_i18n("hi"))], json={"a": "b"})
        result = ProcessResult.coerce((None, "hi", {"a": "b"}))
        self.assertEqual(result, expected)

    def test_coerce_tuple_none_i18n_dict(self):
        expected = ProcessResult(
            errors=[RenderError(I18nMessage("message.id", {"param1": "a"}, None))],
            json={"a": "b"},
        )
        result = ProcessResult.coerce(
            (None, ("message.id", {"param1": "a"}), {"a": "b"})
        )
        self.assertEqual(result, expected)

    def test_coerce_tuple_none_str_none(self):
        expected = ProcessResult(errors=[RenderError(TODO_i18n("hi"))])
        result = ProcessResult.coerce((None, "hi", None))
        self.assertEqual(result, expected)

    def test_coerce_tuple_none_i18n_none(self):
        expected = ProcessResult(
            errors=[RenderError(I18nMessage("message.id", {"param1": "a"}, None))]
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
        with self.assertRaises(ValueError):
            ProcessResult.coerce(("foo", "bar", "baz", "moo"))

    def test_coerce_2tuple_no_dataframe(self):
        with self.assertRaises(ValueError):
            ProcessResult.coerce(("foo", "bar"))

    def test_coerce_2tuple_i18n(self):
        expected = ProcessResult(
            errors=[RenderError(I18nMessage("message_id", {"param1": "a"}, None))]
        )
        result = ProcessResult.coerce(("message_id", {"param1": "a"}))
        self.assertEqual(result, expected)

    def test_coerce_2tuple_bad_i18n_error(self):
        with self.assertRaises(ValueError):
            ProcessResult.coerce(("message_id", None))

    def test_coerce_3tuple_no_dataframe(self):
        with self.assertRaises(ValueError):
            ProcessResult.coerce(("foo", "bar", {"a": "b"}))

    def test_coerce_3tuple_i18n(self):
        self.assertEqual(
            ProcessResult.coerce(("my_id", {"hello": "there"}, "cjwmodule")),
            ProcessResult(
                errors=[
                    RenderError(I18nMessage("my_id", {"hello": "there"}, "cjwmodule"))
                ]
            ),
        )

    def test_coerce_dict_i18n(self):
        expected = ProcessResult(
            errors=[
                RenderError(
                    TODO_i18n("an error"),
                    [
                        QuickFix(
                            I18nMessage("message.id", {}, None),
                            QuickFixAction.PrependStep(
                                "texttodate", {"column": "created_at"}
                            ),
                        )
                    ],
                )
            ]
        )
        result = ProcessResult.coerce(
            {
                "message": "an error",
                "quickFixes": [
                    dict(
                        text=("message.id", {}),
                        action="prependModule",
                        args=["texttodate", {"column": "created_at"}],
                    )
                ],
            }
        )
        self.assertEqual(result, expected)

    def test_coerce_dict_legacy(self):
        dataframe = pd.DataFrame({"A": [1, 2]})
        result = ProcessResult.coerce(
            {
                "dataframe": dataframe,
                "error": "an error",
                "json": {"foo": "bar"},
                "quick_fixes": [],
            }
        )
        expected = ProcessResult(
            dataframe,
            [RenderError(TODO_i18n("an error"), [])],
            json={"foo": "bar"},
        )
        self.assertEqual(result, expected)

    def test_coerce_dict_with_quickfix(self):
        dataframe = pd.DataFrame({"A": [1, 2]})
        result = ProcessResult.coerce(
            {
                "dataframe": dataframe,
                "errors": [
                    {
                        "message": "an error",
                        "quickFixes": [
                            dict(
                                text=("message.id", {}),
                                action="prependModule",
                                args=["texttodate", {"column": "created_at"}],
                            )
                        ],
                    }
                ],
                "json": {"foo": "bar"},
            }
        )
        expected = ProcessResult(
            dataframe,
            [
                RenderError(
                    TODO_i18n("an error"),
                    [
                        QuickFix(
                            I18nMessage("message.id", {}, None),
                            QuickFixAction.PrependStep(
                                "texttodate", {"column": "created_at"}
                            ),
                        )
                    ],
                )
            ],
            json={"foo": "bar"},
        )
        self.assertEqual(result, expected)

    def test_coerce_dict_with_quickfix_not_json_serializable(self):
        dataframe = pd.DataFrame({"A": [1, 2]})
        with self.assertRaises(ValueError):
            ProcessResult.coerce(
                {
                    "dataframe": dataframe,
                    "errors": [
                        {
                            "message": "an error",
                            "quickFixes": [
                                dict(
                                    text="Hi",
                                    action="prependModule",
                                    args=[
                                        "texttodate",
                                        {"columns": pd.Index(["created_at"])},
                                    ],
                                )
                            ],
                        }
                    ],
                    "json": {"foo": "bar"},
                }
            )

    def test_coerce_dict_legacy_with_quickfix_dict(self):
        dataframe = pd.DataFrame({"A": [1, 2]})
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
            errors=[
                RenderError(
                    TODO_i18n("an error"),
                    [
                        QuickFix(
                            TODO_i18n("Hi"),
                            QuickFixAction.PrependStep(
                                "texttodate", {"column": "created_at"}
                            ),
                        )
                    ],
                )
            ],
            json={"foo": "bar"},
        )
        self.assertEqual(result, expected)

    def test_coerce_dict_with_quickfix_dict(self):
        dataframe = pd.DataFrame({"A": [1, 2]})
        result = ProcessResult.coerce(
            {
                "dataframe": dataframe,
                "errors": [
                    {
                        "message": "an error",
                        "quickFixes": [
                            dict(
                                text="Hi",
                                action="prependModule",
                                args=["texttodate", {"column": "created_at"}],
                            )
                        ],
                    }
                ],
                "json": {"foo": "bar"},
            }
        )
        expected = ProcessResult(
            dataframe,
            errors=[
                RenderError(
                    TODO_i18n("an error"),
                    [
                        QuickFix(
                            TODO_i18n("Hi"),
                            QuickFixAction.PrependStep(
                                "texttodate", {"column": "created_at"}
                            ),
                        )
                    ],
                )
            ],
            json={"foo": "bar"},
        )
        self.assertEqual(result, expected)

    def test_coerce_dict_quickfix_multiple(self):
        dataframe = pd.DataFrame({"A": [1, 2]})
        result = ProcessResult.coerce(
            {
                "dataframe": dataframe,
                "errors": [
                    {
                        "message": "an error",
                        "quickFixes": [
                            dict(
                                text="Hi",
                                action="prependModule",
                                args=["texttodate", {"column": "created_at"}],
                            ),
                            dict(
                                text=("message.id", {}),
                                action="prependModule",
                                args=["texttodate", {"column": "created_at"}],
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
                RenderError(
                    TODO_i18n("an error"),
                    [
                        QuickFix(
                            TODO_i18n("Hi"),
                            QuickFixAction.PrependStep(
                                "texttodate", {"column": "created_at"}
                            ),
                        ),
                        QuickFix(
                            I18nMessage("message.id", {}, None),
                            QuickFixAction.PrependStep(
                                "texttodate", {"column": "created_at"}
                            ),
                        ),
                    ],
                ),
                RenderError(TODO_i18n("other error")),
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

    def test_coerce_dict_quickfix_dict_not_json_serializable(self):
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
        with self.assertRaises(ValueError):
            ProcessResult.coerce([None, "foo"])

    @override_settings(MAX_ROWS_PER_TABLE=2)
    def test_truncate_too_big_no_error(self):
        expected_df = pd.DataFrame({"foo": ["bar", "baz"]})
        expected = ProcessResult(
            dataframe=expected_df,
            errors=[
                RenderError(
                    I18nMessage(
                        "py.cjwkernel.pandas.types.ProcessResult.truncate_in_place_if_too_big.warning",
                        {"old_number": 3, "new_number": 2},
                        None,
                    )
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
                RenderError(TODO_i18n("Some error")),
                RenderError(
                    I18nMessage(
                        "py.cjwkernel.pandas.types.ProcessResult.truncate_in_place_if_too_big.warning",
                        {"old_number": 3, "new_number": 2},
                        None,
                    )
                ),
            ],
        )

        result_df = pd.DataFrame({"foo": ["bar", "baz", "moo"]})
        result = ProcessResult(result_df, errors=[RenderError(TODO_i18n("Some error"))])
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
                Column("A", ColumnType.Number()),
                Column("B", ColumnType.Text()),
                Column("C", ColumnType.Timestamp()),
                Column("D", ColumnType.Text()),
            ],
        )

    def test_empty_columns(self):
        result = ProcessResult()
        self.assertEqual(result.column_names, [])
        self.assertEqual(result.columns, [])

    def test_to_arrow_empty_dataframe(self):
        fd, filename = tempfile.mkstemp()
        # We'll test that ProcessResult.to_arrow() writes empty bytes on error
        os.write(fd, b"to-remove")
        os.close(fd)
        try:
            result = ProcessResult.coerce("bad, bad error").to_arrow(Path(filename))
            self.assertEqual(
                result,
                atypes.RenderResult(
                    [RenderError(TODO_i18n("bad, bad error"), [])],
                    {},
                ),
            )
            assert_arrow_table_equals(
                load_untrusted_arrow_file_with_columns(Path(filename))[0], make_table()
            )
        finally:
            os.unlink(filename)

    def test_to_arrow_normal_dataframe(self):
        fd, filename = tempfile.mkstemp()
        try:
            process_result = ProcessResult.coerce(pd.DataFrame({"A": [1, 2]}))
            result = process_result.to_arrow(Path(filename))
            self.assertEqual(
                result,
                atypes.RenderResult(
                    [],
                    {},
                ),
            )
            with pa.ipc.open_file(filename) as reader:
                table = reader.read_all()
            assert_arrow_table_equals(
                table,
                make_table(
                    make_column(
                        # Whatever .format ProcessResult.coerce() gave
                        "A",
                        [1, 2],
                        format=process_result.columns[0].type.format,
                    )
                ),
            )
        finally:
            os.unlink(filename)


class ArrowConversionTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.path = create_tempfile()

    def tearDown(self):
        self.path.unlink()
        super().tearDown()

    def _test_dataframe_to_arrow_table(
        self,
        dataframe: pd.DataFrame,
        columns: List[Column],
        expected_table: pa.Table,
    ) -> None:
        with tempfile_context() as path:
            dataframe_to_arrow_table(dataframe, columns, path)
            # "untrusted": more integration-test-ish
            result_table, result_columns = load_untrusted_arrow_file_with_columns(path)
            assert_arrow_table_equals(result_table, expected_table)
            self.assertEqual(result_columns, columns)  # testing the round trip

    def test_dataframe_all_null_text_column(self):
        self._test_dataframe_to_arrow_table(
            pd.DataFrame({"A": [None]}, dtype=str),
            [Column("A", ColumnType.Text())],
            expected_table=make_table(make_column("A", [None], pa.string())),
        )

    def test_arrow_schema_text_column(self):
        self.assertEqual(
            arrow_schema_to_render_columns(pa.schema([pa.field("A", pa.string())])),
            {"A": RenderColumn("A", "text", None)},
        )

    def test_dataframe_category_column(self):
        self._test_dataframe_to_arrow_table(
            pd.DataFrame({"A": ["A", "B", None, "A"]}, dtype="category"),
            [Column("A", ColumnType.Text())],
            pa.table(
                {
                    "A": pa.DictionaryArray.from_arrays(
                        pa.array([0, 1, None, 0], pa.int8()),
                        pa.array(["A", "B"], pa.string()),
                    ),
                }
            ),
        )

    def test_arrow_schema_category_column(self):
        self.assertEqual(
            arrow_schema_to_render_columns(
                pa.schema([pa.field("A", pa.dictionary(pa.int32(), pa.string()))])
            ),
            {"A": RenderColumn("A", "text", None)},
        )

    def test_dataframe_all_null_category_column(self):
        self._test_dataframe_to_arrow_table(
            pd.DataFrame({"A": [None]}, dtype=str).astype("category"),
            [Column("A", ColumnType.Text())],
            pa.table(
                {
                    "A": pa.DictionaryArray.from_arrays(
                        pa.array([None], pa.int8()),
                        pa.array([], pa.string()),
                    ),
                }
            ),
        )

    def test_dataframe_uint8_column(self):
        self._test_dataframe_to_arrow_table(
            pd.DataFrame({"A": [1, 2, 3, 253]}, dtype=np.uint8),
            [Column("A", ColumnType.Number("{:,d}"))],
            make_table(
                make_column("A", [1, 2, 3, 253], type=pa.uint8(), format="{:,d}")
            ),
        )

    def test_arrow_schema_uint8_column(self):
        self.assertEqual(
            arrow_schema_to_render_columns(
                pa.schema([pa.field("A", pa.uint8(), metadata={"format": "{:,d}"})])
            ),
            {"A": RenderColumn("A", "number", "{:,d}")},
        )

    def test_dataframe_datetime_column(self):
        self._test_dataframe_to_arrow_table(
            pd.DataFrame(
                {"A": ["2019-09-17T21:21:00.123456Z", None]}, dtype="datetime64[ns]"
            ),
            [Column("A", ColumnType.Timestamp())],
            make_table(
                make_column("A", [dt.fromisoformat("2019-09-17T21:21:00.123456"), None])
            ),
        )

    def test_arrow_timestamp_column(self):
        self.assertEqual(
            arrow_schema_to_render_columns(
                pa.schema([pa.field("A", pa.timestamp("ns"))])
            ),
            {"A": RenderColumn("A", "timestamp", None)},
        )

    def test_arrow_date32_column(self):
        self.assertEqual(
            arrow_schema_to_render_columns(
                pa.schema([pa.field("A", pa.date32(), metadata={"unit": "month"})])
            ),
            {"A": RenderColumn("A", "date", "month")},
        )
