import unittest
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from reshape import render


class TestReshape(unittest.TestCase):
    def test_defaults(self):
        params = {'direction': 0, 'colnames': '', 'varcol': ''}
        out = render(pd.DataFrame({'A': [1, 2]}), params)
        # should NOP when first applied
        assert_frame_equal(out, pd.DataFrame({'A': [1, 2]}))

    def test_wide_to_long(self):
        in_table = pd.DataFrame({
            'x': [1, 2, 3],
            'A': ['a', 'b', 'c'],
            'B': ['d', 'e', 'f'],
        })
        params = {'direction': 0, 'colnames': 'x', 'varcol': ''}
        out = render(in_table, params)
        assert_frame_equal(out, pd.DataFrame({
            'x': [1, 1, 2, 2, 3, 3],
            'variable': list('ABABAB'),
            'value': list('adbecf'),
        }))

    def test_wide_to_long_mulicolumn(self):
        """Wide-to-long, with two ID columns."""
        in_table = pd.DataFrame({
            'x': [1, 1, 2, 2, 3, 3],
            'y': [4, 5, 4, 5, 4, 5],
            'A': list('abcdef'),
            'B': list('ghijkl'),
        })
        params = {'direction': 0, 'colnames': 'x,y', 'varcol': ''}
        out = render(in_table, params)
        assert_frame_equal(out, pd.DataFrame({
            'x': [1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3],
            'y': [4, 4, 5, 5, 4, 4, 5, 5, 4, 4, 5, 5],
            'variable': list('ABABABABABAB'),
            'value': list('agbhcidjekfl'),
        }))

    def test_long_to_wide(self):
        in_table = pd.DataFrame({
            'x': [1, 1, 2, 2, 3, 3],
            'variable': list('ABABAB'),
            'value': list('adbecf'),
        })
        params = {'direction': 1, 'colnames': 'x', 'varcol': 'variable'}
        out = render(in_table, params)
        assert_frame_equal(out, pd.DataFrame({
            'x': [1, 2, 3],
            'A': ['a', 'b', 'c'],
            'B': ['d', 'e', 'f'],
        }))

    def test_long_to_wide_missing_varcol(self):
        params = {'direction': 1, 'colnames': 'date', 'varcol': ''}
        out = render(pd.DataFrame({'A': [1, 2]}), params)
        # nop if no column selected
        assert_frame_equal(out, pd.DataFrame({'A': [1, 2]}))

    def test_long_to_wide_checkbox_but_no_second_key(self):
        """has_second_key does nothing if no second column is chosen."""
        in_table = pd.DataFrame({
            'x': [1, 1, 2, 2, 3, 3],
            'variable': list('ABABAB'),
            'value': list('adbecf'),
        })
        params = {
            'direction': 1,
            'colnames': 'x',
            'has_second_key': True,
            'varcol': 'variable'
        }
        out = render(in_table, params)
        assert_frame_equal(out, pd.DataFrame({
            'x': [1, 2, 3],
            'A': ['a', 'b', 'c'],
            'B': ['d', 'e', 'f'],
        }))

    def test_long_to_wide_two_keys(self):
        """Long-to-wide with second_key: identical to two colnames."""
        in_table = pd.DataFrame({
            'x': [1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3],
            'y': [4, 4, 5, 5, 4, 4, 5, 5, 4, 4, 5, 5],
            'variable': list('ABABABABABAB'),
            'value': list('abcdefghijkl'),
        })
        params = {
            'direction': 1,
            'colnames': 'x',
            'has_second_key': True,
            'second_key': 'y',
            'varcol': 'variable'
        }
        out = render(in_table, params)
        assert_frame_equal(out, pd.DataFrame({
            'x': [1, 1, 2, 2, 3, 3],
            'y': [4, 5, 4, 5, 4, 5],
            'A': list('acegik'),
            'B': list('bdfhjl'),
        }))

    def test_long_to_wide_multicolumn(self):
        """Long-to-wide with two ID columns."""
        in_table = pd.DataFrame({
            'x': [1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3],
            'y': [4, 4, 5, 5, 4, 4, 5, 5, 4, 4, 5, 5],
            'variable': list('ABABABABABAB'),
            'value': list('abcdefghijkl'),
        })
        params = {
            'direction': 1,
            'colnames': 'x,y',
            'varcol': 'variable'
        }
        out = render(in_table, params)
        assert_frame_equal(out, pd.DataFrame({
            'x': [1, 1, 2, 2, 3, 3],
            'y': [4, 5, 4, 5, 4, 5],
            'A': list('acegik'),
            'B': list('bdfhjl'),
        }))

    def test_long_to_wide_duplicate_key(self):
        in_table = pd.DataFrame({
            'x': [1, 1],
            'variable': ['A', 'A'],
            'value': ['x', 'y'],
        })
        params = {'direction': 1, 'colnames': 'x', 'varcol': 'variable'}
        out = render(in_table, params)
        self.assertEqual(out, 'Cannot reshape: some variables are repeated')

    def test_transpose(self):
        # Input simulates a table with misplaced headers
        in_table = pd.DataFrame({
            'Name': ['Date', 'Attr'],
            'Dolores': ['2018-04-22', '10'],
            'Robert': ['2016-10-02', None],
            'Teddy': ['2018-04-22', '8']
        }).astype('category')  # cast as Category -- extra-tricky!

        params = {'direction': 2}
        out = render(in_table, params)

        # Keeping the old header for the first column can be confusing.
        # First column header doesnt usually classify rest of headers.
        # Renaming first column header 'New Column'
        ref_table = pd.DataFrame({
            'New Column': ['Dolores', 'Robert', 'Teddy'],
            'Date': ['2018-04-22', '2016-10-02', '2018-04-22'],
            'Attr': ['10', None, '8']
        })

        assert_frame_equal(out, ref_table)


if __name__ == '__main__':
    unittest.main()
