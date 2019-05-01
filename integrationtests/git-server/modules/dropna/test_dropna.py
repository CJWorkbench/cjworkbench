import unittest
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from dropna import migrate_params, render


def P(colnames=[]):
    """Build params."""
    return {
        'colnames': colnames,
    }


class MigrateParamsTest(unittest.TestCase):
    def test_v0_no_colnames(self):
        self.assertEqual(migrate_params({
            'colnames': '',
        }), {
            'colnames': [],
        })

    def test_v0(self):
        self.assertEqual(migrate_params({
            'colnames': 'A,B',
        }), {
            'colnames': ['A', 'B'],
        })

    def test_v1(self):
        self.assertEqual(migrate_params({
            'colnames': ['A', 'B'],
        }), {
            'colnames': ['A', 'B'],
        })


class RenderTest(unittest.TestCase):
    def test_numeric(self):
        result = render(
            pd.DataFrame({'A': [1, np.nan, 3.3], 'B': [np.nan, 'b', 'c']}),
            P(['A'])
        )
        expected = pd.DataFrame({'A': [1, 3.3], 'B': [np.nan, 'c']})
        assert_frame_equal(result, expected)

    def test_string(self):
        result = render(
            pd.DataFrame({'A': [1, 2, 3, 4], 'B': [np.nan, None, '', 'c']}),
            P(['B'])  # drops both '' and np.nan
        )
        expected = pd.DataFrame({'A': [4], 'B': ['c']})
        assert_frame_equal(result, expected)

    def test_datetime(self):
        result = render(
            pd.DataFrame({'A': [pd.NaT, '2019-05-01']},
                         dtype='datetime64[ns]'),
            P(['A'])
        )
        expected = pd.DataFrame({'A': ['2019-05-01']}, dtype='datetime64[ns]')
        assert_frame_equal(result, expected)

    def test_category(self):
        result = render(
            pd.DataFrame({'A': [np.nan, '', 'c']}, dtype='category'),
            P(['A'])  # drops both '' and np.nan
        )
        expected = pd.DataFrame({'A': ['c']}, dtype='category')
        assert_frame_equal(result, expected)

    def test_multiple_columns_drops_union(self):
        result = render(
            pd.DataFrame({'A': [1, np.nan, 3.3], 'B': [np.nan, 'b', 'c']}),
            P(['A', 'B'])
        )
        expected = pd.DataFrame({'A': [3.3], 'B': ['c']})
        assert_frame_equal(result, expected)

    def test_no_colnames(self):
        # No colnames -> do nothing
        result = render(
            pd.DataFrame({'A': ['', np.nan, 'x']}),
            P([])
        )
        expected = pd.DataFrame({'A': ['', np.nan, 'x']})
        assert_frame_equal(result, expected)


if __name__ == '__main__':
    unittest.main()
