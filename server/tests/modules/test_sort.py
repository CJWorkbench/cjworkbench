import datetime
import unittest
import pandas as pd
import numpy as np
from cjworkbench.types import ProcessResult
from server.modules.sort import render, migrate_params
from .util import MockParams


P0 = MockParams.factory(column='', direction=0)
P1 = MockParams.factory(sort_columns=[{ 'colname': '', 'is_ascending': True}], keep_top='')

class SortFromTableTests(unittest.TestCase):
    """
        New v1 of sort includes multi-column sorting. We need to make sure
        the v0 params are migrated correctly (to a single column sort in the new module)
        along with missing params in the array of parameters and general functionality,
        which at the moment is done purely in Pandas.
    """
    # Current direction choices: is_ascending (bool)
    # If the position of the values change, tests will need to be updated

    # NaN and NaT always appear last as the policy in SortFromTable dictates

    def test_parse_v0_column(self):
        params = P0(column='B', direction=1)
        result = migrate_params(params)
        expected = P1(sort_columns=[{'colname': 'B', 'is_ascending': True}], keep_top='')
        self.assertEqual(result, expected)

    # v1 of the module converts missing direction value 0 to is_ascending = True
    def test_parse_v0_direction_missing(self):
        params = P0(column='A', direction=0)
        result = migrate_params(params)
        expected = P1(sort_columns=[{'colname': 'A', 'is_ascending': True}], keep_top='')
        self.assertEqual(result, expected)

    def test_parse_v0_direction_ascending(self):
        params = P0(column='A', direction=1)
        result = migrate_params(params)
        expected = P1(sort_columns=[{'colname': 'A', 'is_ascending': True}], keep_top='')
        self.assertEqual(result, expected)

    def test_parse_v0_direction_descending(self):
        params = P0(column='A', direction=2)
        result = migrate_params(params)
        expected = P1(sort_columns=[{'colname': 'A', 'is_ascending': False}], keep_top='')
        self.assertEqual(result, expected)

    def test_parse_v0_missing_column(self):
        params = P0()
        params.pop('column', None)
        with self.assertRaises(ValueError) as err:
            result = migrate_params(params)
        self.assertEqual('Sort is missing "column" key', str(err.exception))

    def test_parse_v0_missing_direction(self):
        params = P0()
        params.pop('direction', None)
        with self.assertRaises(ValueError) as err:
            result = migrate_params(params)
        self.assertEqual('Sort is missing "direction" key', str(err.exception))

    def test_params_duplicate_columns(self):
        params = P1(sort_columns=[
            {'colname': 'A', 'is_ascending': False},
            {'colname': 'A', 'is_ascending': False}
        ], keep_top='')

        result = render(pd.DataFrame(), params)
        expected = ProcessResult(pd.DataFrame(), error='Duplicate columns.')
        self.assertEqual(result, expected)

    def test_params_null_first_column(self):
        params = P1(sort_columns=[
            {'colname': '', 'is_ascending': False}
        ], keep_top='')

        result = render(pd.DataFrame(), params)
        expected = ProcessResult(pd.DataFrame(), error='Please select a column.')
        self.assertEqual(result, expected)

    def test_params_null_columns(self):
        params = P1(sort_columns=[
            {'colname': 'A', 'is_ascending': False},
            {'colname': '', 'is_ascending': False},
            {'colname': 'B', 'is_ascending': False}
        ], keep_top='')

        result = render(pd.DataFrame(), params)
        expected = ProcessResult(pd.DataFrame(), error='Please select a column.')
        self.assertEqual(result, expected)

    def test_params_str_keep_top(self):
        params = P1(sort_columns=[
            {'colname': 'A', 'is_ascending': False}
        ], keep_top='apple')

        table = pd.DataFrame({'A': ['a', 'b']})
        result = render(table, params)
        expected = ProcessResult(table, error='Please enter an integer in "Keep top" or leave it blank.')
        self.assertEqual(result, expected)

    def test_order_str_ascending(self):
        table = pd.DataFrame({'A': ['a', 'c', 'b'], 'B': [1, 2, 3]})
        params = P1(sort_columns=[{'colname': 'A', 'is_ascending': True}], keep_top='')
        result = render(table, params)
        expected = ProcessResult(
            pd.DataFrame({'A': ['a', 'b', 'c'], 'B': [1, 3, 2]})
        )
        result.dataframe.reset_index(drop=True, inplace=True)
        self.assertEqual(result, expected)

    def test_order_cat_str_ascending(self):
        table = pd.DataFrame({'A': ['a', 'c', 'b'], 'B': [1, 2, 3]})
        table['A'] = table['A'].astype('category')
        params = P1(sort_columns=[{'colname': 'A', 'is_ascending': True}], keep_top='')
        result = render(table, params)
        expected = ProcessResult(
            pd.DataFrame({'A': ['a', 'b', 'c'], 'B': [1, 3, 2]})
        )
        expected.dataframe['A'] = expected.dataframe['A'].astype('category')
        result.dataframe.reset_index(drop=True, inplace=True)
        self.assertEqual(result, expected)

    def test_order_str_descending(self):
        table = pd.DataFrame({'A': ['a', 'c', 'b'], 'B': [1, 2, 3]})
        params = P1(sort_columns=[{'colname': 'A', 'is_ascending': False}], keep_top='')
        result = render(table, params)
        expected = ProcessResult(
            pd.DataFrame({'A': ['c', 'b', 'a'], 'B': [2, 3, 1]})
        )
        result.dataframe.reset_index(drop=True, inplace=True)
        self.assertEqual(result, expected)

    def test_order_number_ascending(self):
        table = pd.DataFrame({'A': [3.0, np.nan, 2.1], 'B': ['a', 'b', 'c']})
        params = P1(sort_columns=[{'colname': 'A', 'is_ascending': True}], keep_top='')
        result = render(table, params)
        expected = ProcessResult(
            pd.DataFrame({'A': [2.1, 3.0, np.nan], 'B': ['c', 'a', 'b']})
        )
        result.dataframe.reset_index(drop=True, inplace=True)
        self.assertEqual(result, expected)

    def test_order_number_descending(self):
        table = pd.DataFrame({'A': [3.0, np.nan, 2.1], 'B': ['a', 'b', 'c']})
        params = P1(sort_columns=[{'colname': 'A', 'is_ascending': False}], keep_top='')
        result = render(table, params)
        expected = ProcessResult(
            pd.DataFrame({'A': [3.0, 2.1, np.nan], 'B': ['a', 'c', 'b']})
        )
        result.dataframe.reset_index(drop=True, inplace=True)
        self.assertEqual(result, expected)

    def test_order_date(self):
        d1 = datetime.datetime(2018, 8, 15, 1, 23, 45)
        d2 = datetime.datetime(2018, 8, 15, 1, 34, 56)
        table = pd.DataFrame({'A': [d2, d1], 'B': ['a', 'b']})
        params = P1(sort_columns=[{'colname': 'A', 'is_ascending': True}], keep_top='')
        result = render(table, params)
        expected = ProcessResult(
            pd.DataFrame({'A': [d1, d2], 'B': ['b', 'a']})
        )
        result.dataframe.reset_index(drop=True, inplace=True)
        self.assertEqual(result, expected)

    def test_keep_top(self):
        d1 = datetime.datetime(2018, 8, 15, 1, 23, 45)
        table = pd.DataFrame({'A': ['b', 'b', 'b', 'a', 'a'], 'B': [d1, d1, d1, d1, d1]})
        params = P1(sort_columns=[{'colname': 'A', 'is_ascending': True}], keep_top='1')
        result = render(table, params)
        expected = ProcessResult(
            pd.DataFrame({'A': ['a', 'b'], 'B': [d1, d1]})
        )
        result.dataframe.reset_index(drop=True, inplace=True)
        self.assertEqual(result, expected)
