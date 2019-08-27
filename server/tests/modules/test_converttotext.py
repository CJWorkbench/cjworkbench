import unittest
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from cjwkernel.pandas.types import RenderColumn
from server.modules.converttotext import migrate_params, render


class MigrateParamsTest(unittest.TestCase):
    def test_v0_no_colnames(self):
        self.assertEqual(migrate_params({"colnames": ""}), {"colnames": []})

    def test_v0(self):
        self.assertEqual(migrate_params({"colnames": "A,B"}), {"colnames": ["A", "B"]})

    def test_v1(self):
        self.assertEqual(
            migrate_params({"colnames": ["A", "B"]}), {"colnames": ["A", "B"]}
        )


class RenderTest(unittest.TestCase):
    def test_NOP(self):
        # should NOP when first applied
        result = render(
            pd.DataFrame({"A": [0.006]}),
            {"colnames": []},
            input_columns={"A": RenderColumn("A", "number", "{:.2f}")},
        )
        assert_frame_equal(result, pd.DataFrame({"A": [0.006]}))

    def test_convert_str(self):
        result = render(
            pd.DataFrame({"A": ["a"]}),
            {"colnames": ["A"]},
            input_columns={"A": RenderColumn("A", "text", None)},
        )
        assert_frame_equal(result, pd.DataFrame({"A": ["a"]}))

    def test_convert_int(self):
        result = render(
            pd.DataFrame({"A": [1], "B": [2]}),
            {"colnames": ["A", "B"]},
            input_columns={
                "A": RenderColumn("A", "number", "{:.2f}"),
                "B": RenderColumn("B", "number", "{:d}"),
            },
        )
        assert_frame_equal(result, pd.DataFrame({"A": ["1.00"], "B": ["2"]}))

    def test_convert_float(self):
        result = render(
            pd.DataFrame({"A": [1.111], "B": [2.6]}),
            {"colnames": ["A", "B"]},
            input_columns={
                "A": RenderColumn("A", "number", "{:.2f}"),
                "B": RenderColumn("B", "number", "{:d}"),
            },
        )
        assert_frame_equal(result, pd.DataFrame({"A": ["1.11"], "B": ["2"]}))

    def test_convert_numbers_all_null(self):
        result = render(
            pd.DataFrame({"A": [np.nan, np.nan]}, dtype=np.float64),
            {"colnames": ["A"]},
            input_columns={"A": RenderColumn("A", "number", "{:d}")},
        )
        assert_frame_equal(result, pd.DataFrame({"A": [np.nan, np.nan]}, dtype=object))

    def test_convert_datetime(self):
        result = render(
            pd.DataFrame(
                {"A": [np.datetime64("2018-01-01"), np.datetime64("2019-02-13")]}
            ),
            {"colnames": ["A"]},
            input_columns={"A": RenderColumn("A", "datetime", None)},
        )
        assert_frame_equal(result, pd.DataFrame({"A": ["2018-01-01", "2019-02-13"]}))

    def test_convert_null(self):
        result = render(
            pd.DataFrame({"A": [1, np.nan]}),
            {"colnames": ["A"]},
            input_columns={"A": RenderColumn("A", "number", "{:,d}")},
        )
        assert_frame_equal(result, pd.DataFrame({"A": ["1", np.nan]}))


if __name__ == "__main__":
    unittest.main()
