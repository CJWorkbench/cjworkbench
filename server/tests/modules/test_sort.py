import datetime
import unittest
import pandas as pd
from pandas.testing import assert_frame_equal
import numpy as np
from server.modules.sort import render, migrate_params


def P(sort_columns=[], keep_top=''):
    return {
        'sort_columns': sort_columns,
        'keep_top': keep_top,
    }


class MigrateParamsTests(unittest.TestCase):
    # New v2 of sort includes string param 'keep_top',
    # v1 of sort includes multi-column sorting. We need to make sure
    # the v0 params are migrated correctly (to a single column sort in the new
    # module) along with missing params in the array of parameters and general
    # functionality, which at the moment is done purely in Pandas.

    def test_migrate_params_v0_column(self):
        result = migrate_params({'column': 'B', 'direction': 1})
        self.assertEqual(result, {
            'sort_columns': [{'colname': 'B', 'is_ascending': True}],
            'keep_top': '',
        })

    def test_migrate_params_v0_direction_none(self):
        # v0 of the module converts missing direction value 0 to ascending
        result = migrate_params({'column': 'A', 'direction': 0})
        self.assertEqual(result, {
            'sort_columns': [{'colname': 'A', 'is_ascending': True}],
            'keep_top': '',
        })

    def test_migrate_params_v0_direction_ascending(self):
        result = migrate_params({'column': 'A', 'direction': 1})
        self.assertEqual(result, {
            'sort_columns': [{'colname': 'A', 'is_ascending': True}],
            'keep_top': '',
        })

    def test_migrate_params_v0_direction_descending(self):
        result = migrate_params({'column': 'A', 'direction': 2})
        self.assertEqual(result, {
            'sort_columns': [{'colname': 'A', 'is_ascending': False}],
            'keep_top': '',
        })

    def test_migrate_params_v0_missing_column(self):
        result = migrate_params({'column': '', 'direction': 2})
        self.assertEqual(result, {
            'sort_columns': [{'colname': '', 'is_ascending': False}],
            'keep_top': '',
        })

    def test_migrate_params_v1(self):
        result = migrate_params({
            'sort_columns': [{'colname': '', 'is_ascending': True}],
        })
        self.assertEqual(result, {
            'sort_columns': [{'colname': '', 'is_ascending': True}],
            'keep_top': '',
        })

    def test_migrate_params_v2(self):
        result = migrate_params({
            'sort_columns': [{'colname': '', 'is_ascending': True}],
            'keep_top': '3',
        })
        self.assertEqual(result, {
            'sort_columns': [{'colname': '', 'is_ascending': True}],
            'keep_top': '3',
        })


class SortTests(unittest.TestCase):
    def test_params_duplicate_columns(self):
        params = P([
            {'colname': 'A', 'is_ascending': False},
            {'colname': 'A', 'is_ascending': False}
        ])

        result = render(pd.DataFrame(), params)
        self.assertEqual(result, 'Duplicate columns.')

    def test_params_initial_value_is_no_op(self):
        params = P([{'colname': '', 'is_ascending': False}])
        result = render(pd.DataFrame(pd.DataFrame({'A': [1, 2]})), params)
        assert_frame_equal(result, pd.DataFrame({'A': [1, 2]}))

    def test_params_nix_empty_columns(self):
        params = P([
            {'colname': 'A', 'is_ascending': False},
            {'colname': '', 'is_ascending': False},
            {'colname': 'B', 'is_ascending': False}
        ])

        result = render(pd.DataFrame({
            'A': [3, 2, 1],
            'B': [2, 3, 4],
            'C': [1, 2, 3],
        }), params)
        assert_frame_equal(result, pd.DataFrame({
            'A': [3, 2, 1],
            'B': [2, 3, 4],
            'C': [1, 2, 3],
        }))

    def test_params_keep_top_str_is_error(self):
        params = P([{'colname': 'A', 'is_ascending': False}], keep_top='apple')

        result = render(pd.DataFrame({'A': [1, 2, 3]}), params)
        expected = (
            'Please enter a positive integer in "Keep top" or leave it blank.'
        )
        self.assertEqual(result, expected)

    def test_params_keep_top_negative_is_error(self):
        params = P([{'colname': 'A', 'is_ascending': False}], keep_top='-2')

        result = render(pd.DataFrame({'A': [1, 2, 3]}), params)
        expected = (
            'Please enter a positive integer in "Keep top" or leave it blank.'
        )
        self.assertEqual(result, expected)

    def test_order_str_ascending(self):
        table = pd.DataFrame({'A': ['a', 'c', 'b'], 'B': [1, 2, 3]})
        params = P([{'colname': 'A', 'is_ascending': True}])
        result = render(table, params)
        expected = pd.DataFrame({'A': ['a', 'b', 'c'], 'B': [1, 3, 2]})
        assert_frame_equal(result, expected)

    def test_order_cat_str_ascending(self):
        table = pd.DataFrame({'A': ['a', 'c', 'b'], 'B': [1, 2, 3]})
        table['A'] = table['A'].astype('category')
        params = P([{'colname': 'A', 'is_ascending': True}])
        result = render(table, params)
        expected = pd.DataFrame({
            'A': pd.Series(['a', 'b', 'c'], dtype='category'),
            'B': [1, 3, 2]
        })
        assert_frame_equal(result, expected)

    def test_order_str_descending(self):
        table = pd.DataFrame({'A': ['a', 'c', 'b'], 'B': [1, 2, 3]})
        params = P([{'colname': 'A', 'is_ascending': False}])
        result = render(table, params)
        expected = pd.DataFrame({'A': ['c', 'b', 'a'], 'B': [2, 3, 1]})
        assert_frame_equal(result, expected)

    def test_order_number_ascending(self):
        # NaN and NaT always appear last
        table = pd.DataFrame({'A': [3.0, np.nan, 2.1], 'B': ['a', 'b', 'c']})
        params = P([{'colname': 'A', 'is_ascending': True}])
        result = render(table, params)
        expected = pd.DataFrame({
            'A': [2.1, 3.0, np.nan],
            'B': ['c', 'a', 'b'],
        })
        assert_frame_equal(result, expected)

    def test_order_number_descending(self):
        table = pd.DataFrame({'A': [3.0, np.nan, 2.1], 'B': ['a', 'b', 'c']})
        params = P([{'colname': 'A', 'is_ascending': False}])
        result = render(table, params)
        expected = pd.DataFrame({
            'A': [3.0, 2.1, np.nan],
            'B': ['a', 'c', 'b'],
        })
        assert_frame_equal(result, expected)

    def test_order_date(self):
        d1 = datetime.datetime(2018, 8, 15, 1, 23, 45)
        d2 = datetime.datetime(2018, 8, 15, 1, 34, 56)
        table = pd.DataFrame({'A': [d2, d1], 'B': ['a', 'b']})
        params = P([{'colname': 'A', 'is_ascending': True}])
        result = render(table, params)
        expected = pd.DataFrame({'A': [d1, d2], 'B': ['b', 'a']})
        assert_frame_equal(result, expected)

    def test_keep_top_2_columns(self):
        table = pd.DataFrame({
            'A': ['a', 'a', 'b', 'b', 'c', 'c'],
            'B': ['a', 'b', 'a', 'b', 'a', 'b'],
            'C': [1, 2, 3, 4, 5, 6],
        })
        params = P([
            {'colname': 'A', 'is_ascending': True},
            {'colname': 'B', 'is_ascending': False},
        ], keep_top='1')
        result = render(table, params)
        assert_frame_equal(result, pd.DataFrame({
            'A': ['a', 'b', 'c'],
            'B': ['b', 'b', 'b'],
            'C': [2, 4, 6],
        }))

    def test_keep_top_N_columns(self):
        """First N-1 columns are "group"; last column is "sort-in-group"."""
        table = pd.DataFrame({
            # Groups are "acf", "adf", "bde" (read this code vertically)
            'A': ['a', 'b', 'a', 'a', 'a', 'b'],
            'B': ['c', 'd', 'c', 'c', 'd', 'd'],
            'C': ['f', 'e', 'f', 'f', 'f', 'e'],
            'D': [1, 2, 3, 4, 5, 6],
        })
        params = P([
            {'colname': 'A', 'is_ascending': True},
            {'colname': 'B', 'is_ascending': True},
            {'colname': 'C', 'is_ascending': False},
            {'colname': 'D', 'is_ascending': False},
        ], keep_top='2')
        result = render(table, params)
        assert_frame_equal(result, pd.DataFrame({
            'A': ['a', 'a', 'a', 'b', 'b'],
            'B': ['c', 'c', 'd', 'd', 'd'],
            'C': ['f', 'f', 'f', 'e', 'e'],
            'D': [4, 3, 5, 6, 2],
        }))

    def test_keep_top_na_is_sorted_last(self):
        nan = np.nan  # to make the table line up -- ASCII art FTW
        table = pd.DataFrame({
            # groups:
            # nan -- not a real group
            # 'a' -- 3 rows
            # 'b' -- 1 group
            'A': [nan, 'a', 'a', 'a', 'b'],
            'B': ['c', 'c', 'd', nan, nan],
            'C': [1, 2, 3, 4, 5],
        })
        params = P([
            {'colname': 'A', 'is_ascending': True},
            {'colname': 'B', 'is_ascending': False},
        ], keep_top='2')
        result = render(table, params)
        assert_frame_equal(result, pd.DataFrame({
            'A': ['a', 'a', 'b', nan],
            'B': ['d', 'c', nan, 'c'],
            'C': [3, 2, 5, 1],
        }))

    def test_keep_top_with_one_column(self):
        table = pd.DataFrame({
            'A': [np.nan, 'a', 'a', 'a', 'b'],
            'B': [1, 2, 3, 4, 5],
        })
        params = P([{'colname': 'A', 'is_ascending': True}], keep_top='2')
        result = render(table, params)
        assert_frame_equal(result, pd.DataFrame({
            'A': ['a', 'a'],
            'B': [2, 3],
        }))

    def test_keep_top_removes_unused_categories(self):
        table = pd.DataFrame({
            'A': [1, 2, 3, 4, 5],
            'B': pd.Series(['x', 'y', 'z', 'a', 'b'], dtype='category'),
        })
        params = P([{'colname': 'A', 'is_ascending': True}], keep_top='2')
        result = render(table, params)
        assert_frame_equal(result, pd.DataFrame({
            'A': [1, 2],
            'B': pd.Series(['x', 'y'], dtype='category'),
        }))
