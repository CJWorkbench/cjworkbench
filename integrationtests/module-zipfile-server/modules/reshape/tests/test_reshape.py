import unittest
from typing import NamedTuple

import numpy as np
import pandas as pd
from cjwmodule.testing.i18n import cjwmodule_i18n_message, i18n_message
from pandas.testing import assert_frame_equal

from reshape import migrate_params, render


class Column(NamedTuple):
    name: str
    type: str


class DefaultSettings(NamedTuple):
    MAX_COLUMNS_PER_TABLE: int = 1000
    MAX_BYTES_PER_COLUMN_NAME: int = 100


DefaultKwargs = {
    "input_columns": "most code does not look at this",
    "settings": DefaultSettings(),
}


def P(
    operation="widetolong",
    key_colnames=[],
    wtl_varcolname="variable",
    wtl_valcolname="value",
    ltw_varcolname="",
):
    return dict(
        operation=operation,
        key_colnames=key_colnames,
        wtl_varcolname=wtl_varcolname,
        wtl_valcolname=wtl_valcolname,
        ltw_varcolname=ltw_varcolname,
    )


class TestReshape(unittest.TestCase):
    def test_defaults(self):
        # should NOP when first applied
        out = render(pd.DataFrame({"A": [1, 2]}), P(), **DefaultKwargs)
        assert_frame_equal(out, pd.DataFrame({"A": [1, 2]}))

    def test_wide_to_long(self):
        in_table = pd.DataFrame({"x": [1, 2, 3], "A": [4, 5, 6], "B": [7, 8, 9]})
        out = render(
            in_table,
            P("widetolong", ["x"], wtl_varcolname="variable", wtl_valcolname="value"),
            **DefaultKwargs
        )
        assert_frame_equal(
            out,
            pd.DataFrame(
                {
                    "x": [1, 1, 2, 2, 3, 3],
                    "variable": list("ABABAB"),
                    "value": [4, 7, 5, 8, 6, 9],
                }
            ),
        )

    def test_wide_to_long_varcolname_conflict(self):
        out = render(
            pd.DataFrame({"A": [1], "B": [2], "C": [3]}),
            P("widetolong", ["A"], wtl_varcolname="A", wtl_valcolname="C"),
            **DefaultKwargs
        )
        self.assertEqual(
            out,
            (
                None,
                [i18n_message("wide_to_long.badColumns.varcolname.conflict")],
            ),
        )

    def test_wide_to_long_valcolname_conflict(self):
        out = render(
            pd.DataFrame({"A": [1], "B": [2], "C": [3]}),
            P("widetolong", ["A"], wtl_varcolname="C", wtl_valcolname="A"),
            **DefaultKwargs
        )
        self.assertEqual(
            out,
            (None, [i18n_message("wide_to_long.badColumns.valcolname.conflict")]),
        )

    def test_wide_to_long_mixed_value_types(self):
        in_table = pd.DataFrame({"X": ["x", "y"], "A": [1, 2], "B": ["y", np.nan]})
        result = render(in_table, P("widetolong", ["X"]), **DefaultKwargs)
        assert_frame_equal(
            result[0],
            pd.DataFrame(
                {
                    "X": ["x", "x", "y", "y"],
                    "variable": ["A", "B", "A", "B"],
                    "value": ["1", "y", "2", np.nan],
                }
            ),
        )
        self.assertEqual(
            result[1],
            {
                "message": i18n_message(
                    "wide_to_long.badColumns.mixedTypes.message",
                    {"n_columns": 1, "first_colname": "A"},
                ),
                "quickFixes": [
                    {
                        "text": i18n_message(
                            "wide_to_long.badColumns.mixedTypes.quick_fix.text",
                            {"n_columns": 1},
                        ),
                        "action": "prependModule",
                        "args": ["converttotext", {"colnames": ["A"]}],
                    }
                ],
            },
        )
        self.assertIsInstance(result[1]["quickFixes"][0]["args"][1]["colnames"], list)

    def test_wide_to_long_no_values_or_variables_categorical_id_var(self):
        result = render(
            pd.DataFrame({"A": []}, dtype="category"),
            P("widetolong", ["A"]),
            **DefaultKwargs
        )
        assert_frame_equal(
            result, pd.DataFrame({"A": [], "variable": [], "value": []}, dtype=str)
        )

    def test_long_to_wide(self):
        in_table = pd.DataFrame(
            {
                "x": [1, 1, 2, 2, 3, 3],
                "variable": list("ABABAB"),
                "value": list("adbecf"),
            }
        )
        out = render(
            in_table, P("longtowide", ["x"], ltw_varcolname="variable"), **DefaultKwargs
        )
        assert_frame_equal(
            out,
            pd.DataFrame({"x": [1, 2, 3], "A": ["a", "b", "c"], "B": ["d", "e", "f"]}),
        )

    def test_long_to_wide_categoricals(self):
        in_table = pd.DataFrame(
            {"x": list("112233"), "variable": list("ABABAB"), "value": list("adbecf")},
            dtype="category",
        )
        out = render(
            in_table, P("longtowide", ["x"], ltw_varcolname="variable"), **DefaultKwargs
        )
        assert_frame_equal(
            out,
            pd.DataFrame(
                {
                    "x": pd.Series(["1", "2", "3"], dtype="category"),
                    "A": pd.Series(["a", "b", "c"], dtype="category"),
                    "B": pd.Series(["d", "e", "f"], dtype="category"),
                }
            ),
        )

    def test_long_to_wide_nix_unused_category(self):
        # https://www.pivotaltracker.com/story/show/174929299
        in_table = pd.DataFrame(
            {
                "A": list("aab"),
                "B": pd.Series([None, None, "c"], dtype="category"),
                "value": list("abc"),
            },
        )
        out = render(
            in_table, P("longtowide", ["A"], ltw_varcolname="B"), **DefaultKwargs
        )
        assert_frame_equal(
            out[0],
            pd.DataFrame(
                {
                    "A": ["b"],
                    "c": ["c"],
                }
            ),
        )
        # There's also a long_to_wide.badRows.emptyColumnHeaders.warning, but that's
        # not under test here

    def test_long_to_wide_treat_empty_string_category_as_empty_string(self):
        # https://www.pivotaltracker.com/story/show/174929289
        in_table = pd.DataFrame(
            {
                "A": ["a", "b"],
                "B": pd.Series(["", ""], dtype="category"),
                "C": [1, 2],
            }
        )
        out = render(
            in_table, P("longtowide", ["A"], ltw_varcolname="B"), **DefaultKwargs
        )
        assert_frame_equal(out[0], pd.DataFrame({"A": pd.Series([], dtype=object)}))
        # there's also a long_to_wide.badRows.emptyColumnHeaders.warning, but that's
        # not under test here

    def test_long_to_wide_missing_varcol(self):
        out = render(
            pd.DataFrame({"A": [1, 2]}),
            P("longtowide", ["date"], ltw_varcolname=""),
            **DefaultKwargs
        )
        # nop if no column selected
        assert_frame_equal(out, pd.DataFrame({"A": [1, 2]}))

    def test_long_to_wide_convert_to_str(self):
        in_table = pd.DataFrame(
            {
                "x": [1, 1, 2, 2, 3, 3],
                "variable": [4, 5, 4, 5, 4, 5],
                "value": list("adbecf"),
            }
        )
        result = render(
            in_table, P("longtowide", ["x"], ltw_varcolname="variable"), **DefaultKwargs
        )
        assert_frame_equal(
            result[0],
            pd.DataFrame({"x": [1, 2, 3], "4": ["a", "b", "c"], "5": ["d", "e", "f"]}),
        )
        self.assertEqual(
            result[1],
            [
                {
                    "message": i18n_message(
                        "long_to_wide.badColumn.notText.message",
                        {"column_name": "variable"},
                    ),
                    "quickFixes": [
                        {
                            "text": i18n_message(
                                "long_to_wide.badColumn.notText.quick_fix.text",
                                {"column_name": "variable"},
                            ),
                            "action": "prependModule",
                            "args": ["converttotext", {"colnames": ["variable"]}],
                        }
                    ],
                }
            ],
        )

    def test_long_to_wide_multicolumn(self):
        """Long-to-wide with second_key: identical to two colnames."""
        in_table = pd.DataFrame(
            {
                "x": [1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3],
                "y": [4, 4, 5, 5, 4, 4, 5, 5, 4, 4, 5, 5],
                "variable": list("ABABABABABAB"),
                "value": list("abcdefghijkl"),
            }
        )
        out = render(
            in_table,
            P("longtowide", ["x", "y"], ltw_varcolname="variable"),
            **DefaultKwargs
        )
        assert_frame_equal(
            out,
            pd.DataFrame(
                {
                    "x": [1, 1, 2, 2, 3, 3],
                    "y": [4, 5, 4, 5, 4, 5],
                    "A": list("acegik"),
                    "B": list("bdfhjl"),
                }
            ),
        )

    def test_long_to_wide_duplicate_key(self):
        in_table = pd.DataFrame(
            {"x": [1, 1], "variable": ["A", "A"], "value": ["x", "y"]}
        )
        out = render(
            in_table, P("longtowide", ["x"], ltw_varcolname="variable"), **DefaultKwargs
        )
        self.assertEqual(out, i18n_message("long_to_wide.error.repeatedVariables"))

    def test_long_to_wide_varcol_in_key(self):
        in_table = pd.DataFrame(
            {"x": ["1", "2"], "variable": ["A", "B"], "value": ["a", "b"]}
        )
        out = render(
            in_table, P("longtowide", ["x"], ltw_varcolname="x"), **DefaultKwargs
        )
        self.assertEqual(out, i18n_message("error.sameColumnAndRowVariables"))

    def test_long_to_wide_nix_empty(self):
        in_table = pd.DataFrame(
            {"x": [1, 2, 3], "variable": ["", np.nan, "foo"], "value": ["a", "b", "c"]}
        )
        result = render(
            in_table, P("longtowide", ["x"], ltw_varcolname="variable"), **DefaultKwargs
        )
        assert_frame_equal(result[0], pd.DataFrame({"x": [3], "foo": ["c"]}))
        self.assertEqual(
            result[1],
            [
                i18n_message(
                    "long_to_wide.badRows.emptyColumnHeaders.warning",
                    {"n_rows": 2, "column_name": "variable"},
                )
            ],
        )

    def test_long_to_wide_nix_empty_leaving_empty_table(self):
        in_table = pd.DataFrame(
            {"x": [1, 2], "variable": ["", np.nan], "value": ["a", "b"]}
        )
        result = render(
            in_table, P("longtowide", ["x"], ltw_varcolname="variable"), **DefaultKwargs
        )
        assert_frame_equal(result[0], pd.DataFrame({"x": pd.Series([], dtype=int)}))
        self.assertEqual(
            result[1],
            [
                i18n_message(
                    "long_to_wide.badRows.emptyColumnHeaders.warning",
                    {"n_rows": 2, "column_name": "variable"},
                )
            ],
        )

    def test_long_to_wide_error_too_many_columns(self):
        in_table = pd.DataFrame(
            {
                "x": [1, 2],
                "variable": ["y", "y"],
                "value": ["a", "b"],
                "other": ["", ""],
            }
        )
        result = render(
            in_table, P("longtowide", ["x"], ltw_varcolname="variable"), **DefaultKwargs
        )
        self.assertEqual(result, i18n_message("long_to_wide.error.tooManyValueColumns"))

    def test_long_to_wide_error_not_enough_columns(self):
        in_table = pd.DataFrame({"x": [1, 2], "variable": ["y", "y"]})
        result = render(
            in_table, P("longtowide", ["x"], ltw_varcolname="variable"), **DefaultKwargs
        )
        self.assertEqual(result, i18n_message("long_to_wide.error.noValueColumn"))

    def test_long_to_wide_invalid_colname(self):
        in_table = pd.DataFrame({"row": [1], "col": ["a\x00b"], "val": [2]})
        result = render(
            in_table, P("longtowide", ["row"], ltw_varcolname="col"), **DefaultKwargs
        )
        assert_frame_equal(result[0], pd.DataFrame({"row": [1], "ab": [2]}))
        self.assertEqual(
            result[1],
            [
                cjwmodule_i18n_message(
                    "util.colnames.warnings.ascii_cleaned",
                    {"n_columns": 1, "first_colname": "ab"},
                )
            ],
        )

    def test_transpose(self):
        # (Most tests are in the `transpose` module....)
        in_table = pd.DataFrame(
            {
                "Name": ["Date", "Attr"],
                "Dolores": ["2018-04-22", "10"],
                "Robert": ["2016-10-02", None],
                "Teddy": ["2018-04-22", "8"],
            }
        )

        result = render(
            in_table,
            P("transpose"),
            input_columns={
                "Name": Column("Name", "text"),
                "Dolores": Column("Dolores", "text"),
                "Robert": Column("Robert", "text"),
                "Teddy": Column("Teddy", "text"),
            },
            settings=DefaultSettings(),
        )
        # Keeping the old header for the first column can be confusing.
        # First column header doesnt usually classify rest of headers.
        # Renaming first column header 'New Column'
        expected = pd.DataFrame(
            {
                "New Column": ["Dolores", "Robert", "Teddy"],
                "Date": ["2018-04-22", "2016-10-02", "2018-04-22"],
                "Attr": ["10", None, "8"],
            }
        )
        assert_frame_equal(result, expected)

    def test_migrate_v0(self):
        # The menu goes from 'direction: 1' to 'operation: longtowide'
        self.assertEqual(
            migrate_params(
                {
                    "direction": 1,
                    "colnames": "x",
                    "varcol": "var",
                    "has_second_key": True,
                    "second_key": "y",
                }
            ),
            {
                "operation": "longtowide",
                "key_colnames": ["x", "y"],
                "wtl_valcolname": "value",  # wasn't an option before
                "wtl_varcolname": "variable",  # wasn't an option before
                "ltw_varcolname": "var",
            },
        )

    def test_migrate_v1_transpose(self):
        self.assertEqual(
            migrate_params(
                {
                    "direction": "transpose",
                    "colnames": "A",
                    "has_second_key": True,
                    "second_key": "B",
                    "varcol": "var",
                }
            ),
            {
                "operation": "transpose",
                "key_colnames": ["A"],  # useless
                "wtl_valcolname": "value",  # wasn't an option before
                "wtl_varcolname": "variable",  # wasn't an option before
                "ltw_varcolname": "var",
            },
        )

    def test_migrate_v1_longtowide(self):
        self.assertEqual(
            migrate_params(
                {
                    "direction": "longtowide",
                    "colnames": "A",
                    "has_second_key": True,
                    "second_key": "B",
                    "varcol": "var",
                }
            ),
            {
                "operation": "longtowide",
                "key_colnames": ["A", "B"],
                "wtl_valcolname": "value",  # wasn't an option before
                "wtl_varcolname": "variable",  # wasn't an option before
                "ltw_varcolname": "var",
            },
        )

    def test_migrate_v1_widetolong(self):
        self.assertEqual(
            migrate_params(
                {
                    "direction": "widetolong",
                    "colnames": "A",
                    "has_second_key": True,
                    "second_key": "B",
                    "varcol": "var",
                }
            ),
            {
                "operation": "widetolong",
                "key_colnames": ["A"],  # in v1, wtl didn't support second_key
                "wtl_valcolname": "value",  # wasn't an option before
                "wtl_varcolname": "variable",  # wasn't an option before
                "ltw_varcolname": "var",  # unused
            },
        )

    def test_migrate_v2(self):
        self.assertEqual(
            migrate_params(
                {
                    "operation": "widetolong",
                    "key_colnames": ["A"],
                    "wtl_valcolname": "value",
                    "wtl_varcolname": "variable",
                    "ltw_varcolname": "var",
                }
            ),
            {
                "operation": "widetolong",
                "key_colnames": ["A"],
                "wtl_valcolname": "value",
                "wtl_varcolname": "variable",
                "ltw_varcolname": "var",
            },
        )


if __name__ == "__main__":
    unittest.main()
