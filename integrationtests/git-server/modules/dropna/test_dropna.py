import unittest
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from dropna import dropna, render


class TestDropna(unittest.TestCase):
    def test_numeric(self):
        result = pd.DataFrame({'A': [1, np.nan, 3.3], 'B': [np.nan, 'b', 'c']})
        result = dropna(result, ['A'])
        expected = pd.DataFrame({'A': [1, 3.3], 'B': [np.nan, 'c']})
        assert_frame_equal(result, expected)

    def test_string(self):
        result = pd.DataFrame({'A': [1, 2, 3], 'B': [np.nan, '', 'c']})
        result = dropna(result, ['B'])  # Drops both '' and np.nan
        expected = pd.DataFrame({'A': [3], 'B': ['c']})
        assert_frame_equal(result, expected)

    def test_category(self):
        result = pd.DataFrame({'A': [np.nan, '', 'c']}, dtype='category')
        result = dropna(result, ['A'])  # Drops both '' and np.nan
        expected = pd.DataFrame({'A': ['c']}, dtype='category')
        assert_frame_equal(result, expected)

    def test_multiple_columns_gives_intersection(self):
        result = pd.DataFrame({'A': [1, np.nan, 3.3], 'B': [np.nan, 'b', 'c']})
        result = dropna(result, ['A', 'B'])
        expected = pd.DataFrame({'A': [3.3], 'B': ['c']})
        assert_frame_equal(result, expected)


class RenderTest(unittest.TestCase):
    def test_no_colnames(self):
        # No colnames -> do nothing
        result = pd.DataFrame({'A': ['', np.nan, 'x']})
        result = render(result, {'colnames': ''})
        expected = pd.DataFrame({'A': ['', np.nan, 'x']})
        assert_frame_equal(result, expected)

    def test_colnames_comma_separated(self):
        result = pd.DataFrame({
            'A': ['', 'b', 'c'],
            'B': [1.1, np.nan, 3.3],
            'C': ['x', 'y', 'z'],
        })
        result = render(result, {'colnames': 'A,B'})
        expected = pd.DataFrame({'A': ['c'], 'B': [3.3], 'C': ['z']})
        assert_frame_equal(result, expected)

    def test_missing_colname(self):
        result = pd.DataFrame({'A': [1]})
        result = render(result, {'colnames': 'B'})
        self.assertEqual(result, 'You chose a missing column')


if __name__ == '__main__':
    unittest.main()
