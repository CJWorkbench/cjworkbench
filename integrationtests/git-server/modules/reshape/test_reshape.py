import unittest
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from reshape import render, migrate_params


def P(
    direction="widetolong", colnames="", varcol="", has_second_key=False, second_key=""
):
    return {
        "direction": direction,
        "colnames": colnames,
        "varcol": varcol,
        "has_second_key": has_second_key,
        "second_key": second_key,
    }


class TestReshape(unittest.TestCase):
    def test_defaults(self):
        # should NOP when first applied
        out = render(pd.DataFrame({"A": [1, 2]}), P())
        assert_frame_equal(out, pd.DataFrame({"A": [1, 2]}))

    def test_wide_to_long(self):
        in_table = pd.DataFrame({"x": [1, 2, 3], "A": [4, 5, 6], "B": [7, 8, 9]})
        out = render(in_table, P("widetolong", "x"))
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

    def test_wide_to_long_mixed_value_types(self):
        in_table = pd.DataFrame({"X": ["x", "y"], "A": [1, 2], "B": ["y", np.nan]})
        result = render(in_table, P("widetolong", "X"))
        assert_frame_equal(
            result["dataframe"],
            pd.DataFrame(
                {
                    "X": ["x", "x", "y", "y"],
                    "variable": ["A", "B", "A", "B"],
                    "value": ["1", "y", "2", np.nan],
                }
            ),
        )
        self.assertEqual(
            result["error"],
            (
                'Columns "A" were auto-converted to Text because the value column '
                "cannot have multiple types."
            ),
        )
        self.assertEqual(
            result["quick_fixes"],
            [
                {
                    "text": 'Convert "A" to text',
                    "action": "prependModule",
                    "args": ["converttotext", {"colnames": "A"}],
                }
            ],
        )

    def test_wide_to_long_no_values_or_variables_categorical_id_var(self):
        result = render(pd.DataFrame({"A": []}, dtype="category"), P("widetolong", "A"))
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
        out = render(in_table, P("longtowide", "x", "variable"))
        assert_frame_equal(
            out,
            pd.DataFrame({"x": [1, 2, 3], "A": ["a", "b", "c"], "B": ["d", "e", "f"]}),
        )

    def test_long_to_wide_missing_varcol(self):
        out = render(pd.DataFrame({"A": [1, 2]}), P("longtowide", "date", ""))
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
        result = render(in_table, P("longtowide", "x", "variable"))
        assert_frame_equal(
            result["dataframe"],
            pd.DataFrame({"x": [1, 2, 3], "4": ["a", "b", "c"], "5": ["d", "e", "f"]}),
        )
        self.assertEqual(
            result["error"],
            (
                'Column "variable" was auto-converted to Text because column '
                "names must be text."
            ),
        )
        self.assertEqual(
            result["quick_fixes"],
            [
                {
                    "text": 'Convert "variable" to text',
                    "action": "prependModule",
                    "args": ["converttotext", {"colnames": "variable"}],
                }
            ],
        )

    def test_long_to_wide_checkbox_but_no_second_key(self):
        """has_second_key does nothing if no second column is chosen."""
        in_table = pd.DataFrame(
            {
                "x": [1, 1, 2, 2, 3, 3],
                "variable": list("ABABAB"),
                "value": list("adbecf"),
            }
        )
        out = render(in_table, P("longtowide", "x", "variable", has_second_key=True))
        assert_frame_equal(
            out,
            pd.DataFrame({"x": [1, 2, 3], "A": ["a", "b", "c"], "B": ["d", "e", "f"]}),
        )

    def test_long_to_wide_two_keys(self):
        """Long-to-wide with second_key: identical to two colnames."""
        in_table = pd.DataFrame(
            {
                "x": [1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3],
                "y": [4, 4, 5, 5, 4, 4, 5, 5, 4, 4, 5, 5],
                "variable": list("ABABABABABAB"),
                "value": list("abcdefghijkl"),
            }
        )
        out = render(in_table, P("longtowide", "x", "variable", True, "y"))
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
        out = render(in_table, P("longtowide", "x", "variable"))
        self.assertEqual(out, "Cannot reshape: some variables are repeated")

    def test_long_to_wide_varcol_in_key(self):
        in_table = pd.DataFrame(
            {"x": ["1", "2"], "variable": ["A", "B"], "value": ["a", "b"]}
        )
        out = render(in_table, P("longtowide", "x", "x"))
        self.assertEqual(
            out, ("Cannot reshape: column and row variables must be different")
        )

    def test_transpose(self):
        # Input simulates a table with misplaced headers
        in_table = pd.DataFrame(
            {
                "Name": ["Date", "Attr"],
                "Dolores": ["2018-04-22", "10"],
                "Robert": ["2016-10-02", None],
                "Teddy": ["2018-04-22", "8"],
            }
        ).astype(
            "category"
        )  # cast as Category -- extra-tricky!

        out = render(in_table, P("transpose"))

        # Keeping the old header for the first column can be confusing.
        # First column header doesnt usually classify rest of headers.
        # Renaming first column header 'New Column'
        ref_table = pd.DataFrame(
            {
                "New Column": ["Dolores", "Robert", "Teddy"],
                "Date": ["2018-04-22", "2016-10-02", "2018-04-22"],
                "Attr": ["10", None, "8"],
            }
        )

        assert_frame_equal(out, ref_table)

    def test_migrate_v0_to_v1(self):
        v0_params = {"direction": 1, "colnames": "x", "varcol": "variable"}
        v1_params = {"direction": "longtowide", "colnames": "x", "varcol": "variable"}

        new_params = migrate_params(v0_params)
        self.assertEqual(new_params, v1_params)


if __name__ == "__main__":
    unittest.main()
