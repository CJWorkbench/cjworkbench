import unittest
import pandas as pd
from pandas.testing import assert_frame_equal
from server.modules import selectcolumns


def P(colnames, drop_or_keep, select_range, column_numbers):
    return {
        'colnames': colnames,
        'drop_or_keep': drop_or_keep,
        'select_range': select_range,
        'column_numbers': column_numbers,
    }


def render(table, colnames, drop_or_keep, select_range, column_numbers):
    params = P(colnames, drop_or_keep, select_range, column_numbers)
    return selectcolumns.render(table, params)


class SelectColumnsTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.table = pd.DataFrame({'A': [1, 2], 'B': [2, 3], 'C': [3, 4]})

    def test_render_single_column(self):
        result = render(self.table, 'A', 1, False, '')
        assert_frame_equal(result, pd.DataFrame({'A': [1, 2]}))

    def test_render_maintain_input_column_order(self):
        result = render(self.table, 'B,A', 1, False, '')
        assert_frame_equal(result, pd.DataFrame({'A': [1, 2], 'B': [2, 3]}))

    def test_render_ignore_invalid_column_name(self):
        result = render(self.table, 'A,X', 1, False, '')
        assert_frame_equal(result, pd.DataFrame({'A': [1, 2]}))

    def test_render_drop_columns(self):
        result = render(self.table, 'B,C', 0, False, '')
        assert_frame_equal(result, pd.DataFrame({'A': [1, 2]}))

    def test_render_range_comma_separated(self):
        result = render(self.table.copy(), '', 1, True, '1,3')
        assert_frame_equal(result, self.table[['A', 'C']])

    def test_render_range_hyphen_separated(self):
        result = render(self.table.copy(), '', 0, True, '2-3')
        assert_frame_equal(result, pd.DataFrame(self.table[['A']]))

    def test_render_range_overlapping_ranges(self):
        result = render(self.table.copy(), '', 0, True, '2-3,2')
        self.assertEqual(result,
                         'There are overlapping numbers in input range')

    def test_render_range_non_numeric_ranges(self):
        result = render(self.table.copy(), '', 0, True, '2-3,giraffe')
        self.assertEqual(
            result,
            'Rows must look like "1-2", "5" or "1-2, 5"; got "giraffe"'
        )
