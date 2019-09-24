import unittest
import pandas as pd
from pandas.testing import assert_frame_equal
from staticmodules.formatnumbers import migrate_params, render


class MigrateParamsTest(unittest.TestCase):
    def test_v0_empty_colnames(self):
        self.assertEqual(
            migrate_params({"colnames": "", "format": "{:,.1%}"}),
            {"colnames": [], "format": "{:,.1%}"},
        )

    def test_v0(self):
        self.assertEqual(
            migrate_params({"colnames": "A,B", "format": "{:,.1%}"}),
            {"colnames": ["A", "B"], "format": "{:,.1%}"},
        )

    def test_v1(self):
        self.assertEqual(
            migrate_params({"colnames": ["A", "B"], "format": "{:,.1%}"}),
            {"colnames": ["A", "B"], "format": "{:,.1%}"},
        )


class FormatnumbersTest(unittest.TestCase):
    def test_render_empty_is_no_op(self):
        result = render(pd.DataFrame({"A": [1]}), {"colnames": [], "format": "X{:d}"})
        assert_frame_equal(result, pd.DataFrame({"A": [1]}))

    def test_render_multiple_columns(self):
        result = render(
            pd.DataFrame({"A": [1], "B": [2], "C": [3]}),
            {"colnames": ["A", "B"], "format": "X{:d}"},
        )
        assert_frame_equal(
            result["dataframe"], pd.DataFrame({"A": [1], "B": [2], "C": [3]})
        )
        self.assertEqual(result["column_formats"], {"A": "X{:d}", "B": "X{:d}"})
