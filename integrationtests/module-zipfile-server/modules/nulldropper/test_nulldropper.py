import unittest
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from nulldropper import migrate_params, render


class MigrateParamsTests(unittest.TestCase):
    def test_v0(self):
        self.assertEqual(migrate_params({"nulldropper_statictext": ""}), {})

    def test_v1(self):
        self.assertEqual(migrate_params({}), {})


class RenderTests(unittest.TestCase):
    def test_drop_null_objects(self):
        table = pd.DataFrame({"A": [1, 2], "B": [None, None]})
        result = render(table, {})
        assert_frame_equal(result, pd.DataFrame({"A": [1, 2]}))

    def test_drop_nan_floats(self):
        table = pd.DataFrame({"A": [1, 2], "B": [np.nan, np.nan]})
        result = render(table, {})
        assert_frame_equal(result, pd.DataFrame({"A": [1, 2]}))

    def test_drop_empty_strings(self):
        table = pd.DataFrame({"A": [1, 2], "B": ["", ""]})
        result = render(table, {})
        assert_frame_equal(result, pd.DataFrame({"A": [1, 2]}))

    def test_drop_empty_strings_and_null_in_same_column(self):
        table = pd.DataFrame({"A": [1, 2], "B": ["", None]})
        result = render(table, {})
        assert_frame_equal(result, pd.DataFrame({"A": [1, 2]}))

    def test_drop_empty_string_category(self):
        table = pd.DataFrame({"A": [1, 2], "B": ["", ""]})
        table["B"] = table["B"].astype("category")
        result = render(table, {})
        assert_frame_equal(result, pd.DataFrame({"A": [1, 2]}))

    def test_do_not_drop_zeroes(self):
        table = pd.DataFrame({"A": [1, 2], "B": [0, 0]})
        result = render(table, {})
        assert_frame_equal(result, pd.DataFrame({"A": [1, 2], "B": [0, 0]}))


if __name__ == "__main__":
    unittest.main()
