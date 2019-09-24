from typing import Any, Dict, List
import unittest
import pandas as pd
from pandas.testing import assert_frame_equal
from staticmodules.selectcolumns import migrate_params, render


class MigrateParamsTest(unittest.TestCase):
    def test_v0_no_colnames(self):
        self.assertEqual(
            migrate_params(
                {
                    "colnames": "",
                    "select_range": False,
                    "column_numbers": "",
                    "drop_or_keep": 0,
                }
            ),
            {
                "colnames": [],
                "select_range": False,
                "column_numbers": "",
                "keep": False,
            },
        )

    def test_v0_colnames(self):
        self.assertEqual(
            migrate_params(
                {
                    "colnames": "A,B",
                    "select_range": False,
                    "column_numbers": "",
                    "drop_or_keep": 1,
                }
            ),
            {
                "colnames": ["A", "B"],
                "select_range": False,
                "column_numbers": "",
                "keep": True,
            },
        )


def P(
    colnames: List[str] = [],
    select_range: bool = False,
    column_numbers: str = "",
    keep: bool = True,
) -> Dict[str, Any]:
    """Build params dict."""
    return {
        "colnames": colnames,
        "select_range": select_range,
        "column_numbers": column_numbers,
        "keep": keep,
    }


class RenderTest(unittest.TestCase):
    def test_render_single_column(self):
        table = pd.DataFrame({"A": [1, 2], "B": [2, 3], "C": [3, 4]})
        result = render(table, P(["A"]))
        assert_frame_equal(result, pd.DataFrame({"A": [1, 2]}))

    def test_render_maintain_input_column_order(self):
        table = pd.DataFrame({"A": [1, 2], "B": [2, 3], "C": [3, 4]})
        result = render(table, P(["B"], keep=False))
        assert_frame_equal(result, pd.DataFrame({"A": [1, 2], "C": [3, 4]}))

    def test_render_drop_columns(self):
        table = pd.DataFrame({"A": [1, 2], "B": [2, 3], "C": [3, 4]})
        result = render(table, P(["B", "C"], keep=False))
        assert_frame_equal(result, pd.DataFrame({"A": [1, 2]}))

    def test_render_range_ignore_empty_range(self):
        table = pd.DataFrame({"A": [1, 2], "B": [2, 3], "C": [3, 4]})
        result = render(table.copy(), P(select_range=True, column_numbers=""))
        self.assertEqual(
            result, 'Column numbers must look like "1-2", "5" or "1-2, 5"; got ""'
        )

    def test_render_range_comma_separated(self):
        table = pd.DataFrame({"A": [1, 2], "B": [2, 3], "C": [3, 4]})
        result = render(table, P(select_range=True, column_numbers="1,3"))
        assert_frame_equal(result, pd.DataFrame({"A": [1, 2], "C": [3, 4]}))

    def test_render_range_hyphen_separated(self):
        table = pd.DataFrame({"A": [1, 2], "B": [2, 3], "C": [3, 4]})
        result = render(table, P(select_range=True, column_numbers="2-3", keep=False))
        assert_frame_equal(result, pd.DataFrame({"A": [1, 2]}))

    def test_render_range_overlapping_ranges(self):
        table = pd.DataFrame({"A": [1, 2], "B": [2, 3], "C": [3, 4]})
        result = render(table, P(select_range=True, column_numbers="2-3,2"))
        self.assertEqual(result, "There are overlapping numbers in input range")

    def test_render_range_clamp_range(self):
        table = pd.DataFrame({"A": [1, 2], "B": [2, 3], "C": [3, 4]})
        result = render(table, P(select_range=True, column_numbers="-1,2,6"))
        self.assertEqual(
            result, 'Column numbers must look like "1-2", "5" or "1-2, 5"; got "-1"'
        )

    def test_render_range_non_numeric_ranges(self):
        table = pd.DataFrame({"A": [1, 2], "B": [2, 3], "C": [3, 4]})
        result = render(table, P(select_range=True, column_numbers="2-3,giraffe"))
        self.assertEqual(
            result,
            ('Column numbers must look like "1-2", "5" or "1-2, 5"; ' 'got "giraffe"'),
        )
