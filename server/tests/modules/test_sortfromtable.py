import datetime
import unittest
import pandas as pd
import numpy as np
from server.modules.sortfromtable import SortFromTable
from server.modules.types import ProcessResult
from .util import MockParams


P = MockParams.factory(column='', direction=0)


class SortFromTableTests(unittest.TestCase):
    # Current direction choices: "Select|Ascending|Descending"
    # If the position of the values change, tests will need to be updated

    # NaN and NaT always appear last as the policy in SortFromTable dictates

    def test_order_missing_direction(self):
        table = pd.DataFrame({'A': ['a', 'c', 'b'], 'B': [1, 2, 3]})
        # no-op because no direction is specified
        # TODO nix the very _possibility_ of no direction. Why would anybody
        # ever want to sort by no direction?
        params = P(column='A', direction=0)
        result = SortFromTable.render(params, table)
        expected = ProcessResult(
            pd.DataFrame({'A': ['a', 'c', 'b'], 'B': [1, 2, 3]})
        )
        self.assertEqual(result, expected)

    def test_order_str_ascending(self):
        table = pd.DataFrame({'A': ['a', 'c', 'b'], 'B': [1, 2, 3]})
        params = P(column='A', direction=1)
        result = SortFromTable.render(params, table)
        expected = ProcessResult(
            pd.DataFrame({'A': ['a', 'b', 'c'], 'B': [1, 3, 2]})
        )
        self.assertEqual(result, expected)

    def test_order_cat_str_ascending(self):
        table = pd.DataFrame({'A': ['a', 'c', 'b'], 'B': [1, 2, 3]})
        table['A'] = table['A'].astype('category')
        params = P(column='A', direction=1)
        result = SortFromTable.render(params, table)
        expected = ProcessResult(
            pd.DataFrame({'A': ['a', 'b', 'c'], 'B': [1, 3, 2]})
        )
        expected.dataframe['A'] = expected.dataframe['A'].astype('category')
        self.assertEqual(result, expected)

    def test_order_str_descending(self):
        table = pd.DataFrame({'A': ['a', 'c', 'b'], 'B': [1, 2, 3]})
        params = P(column='A', direction=2)
        result = SortFromTable.render(params, table)
        expected = ProcessResult(
            pd.DataFrame({'A': ['c', 'b', 'a'], 'B': [2, 3, 1]})
        )
        self.assertEqual(result, expected)

    def test_order_number_ascending(self):
        table = pd.DataFrame({'A': [3.0, np.nan, 2.1], 'B': ['a', 'b', 'c']})
        params = P(column='A', direction=1)
        result = SortFromTable.render(params, table)
        expected = ProcessResult(
            pd.DataFrame({'A': [2.1, 3.0, np.nan], 'B': ['c', 'a', 'b']})
        )
        self.assertEqual(result, expected)

    def test_order_number_descending(self):
        table = pd.DataFrame({'A': [3.0, np.nan, 2.1], 'B': ['a', 'b', 'c']})
        params = P(column='A', direction=2)
        result = SortFromTable.render(params, table)
        expected = ProcessResult(
            pd.DataFrame({'A': [3.0, 2.1, np.nan], 'B': ['a', 'c', 'b']})
        )
        self.assertEqual(result, expected)

    def test_order_date(self):
        d1 = datetime.datetime(2018, 8, 15, 1, 23, 45)
        d2 = datetime.datetime(2018, 8, 15, 1, 34, 56)
        table = pd.DataFrame({'A': [d2, d1], 'B': ['a', 'b']})
        params = P(column='A', direction=1)
        result = SortFromTable.render(params, table)
        expected = ProcessResult(
            pd.DataFrame({'A': [d1, d2], 'B': ['b', 'a']})
        )
        self.assertEqual(result, expected)
