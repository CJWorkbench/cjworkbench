from collections import namedtuple
import unittest
import pandas as pd
from pandas.testing import assert_frame_equal
from server.modules.duplicatecolumns import render


RenderColumn = namedtuple('RenderColumn', ('format',))


class DuplicateColumnsTests(unittest.TestCase):
    def test_duplicate_column(self):
        table = pd.DataFrame({
            'A': [1, 2],
            'B': [2, 3],
            'C': [3, 4],
        })
        input_columns = {
            'A': RenderColumn('{:,}'),
            'B': RenderColumn('{:,.2f}'),
            'C': RenderColumn('{:,d}'),
        }
        result = render(table, {'colnames': 'A,C'}, input_columns=input_columns)
        expected = pd.DataFrame({
            'A': [1, 2],
            'Copy of A': [1, 2],
            'B': [2, 3],
            'C': [3, 4],
            'Copy of C': [3, 4],
        })
        assert_frame_equal(result['dataframe'], expected)
        self.assertEqual(result['column_formats'], {
            'Copy of A': '{:,}',
            'Copy of C': '{:,d}',
        })

    def test_duplicate_with_existing(self):
        table = pd.DataFrame({
            'A': [1, 2],
            'Copy of A': [2, 3],
            'Copy of A 1': [3, 4],
            'C': [4, 5],
        })
        input_columns = {
            'A': RenderColumn('{:,}'),
            'Copy of A': RenderColumn('{:,.2f}'),
            'Copy of A 1': RenderColumn('{:,.1%}'),
            'C': RenderColumn('{:,d}'),
        }
        result = render(table, {'colnames': 'A'}, input_columns=input_columns)
        expected = pd.DataFrame({
            'A': [1, 2],
            'Copy of A 2': [1, 2],
            'Copy of A': [2, 3],
            'Copy of A 1': [3, 4],
            'C': [4, 5],
        })
        assert_frame_equal(result['dataframe'], expected)
        self.assertEqual(result['column_formats'], {
            'Copy of A 2': '{:,}',
        })
