import io
import unittest
import pandas as pd
from server.modules.selectcolumns import SelectColumns
from server.modules.types import ProcessResult

KEEP = 1
DROP = 0


class MockWfModule:
    def __init__(self, colnames, drop_or_keep, select_range, column_numbers):
        self.colnames = colnames
        self.drop_or_keep = drop_or_keep
        self.select_range = select_range
        self.column_numbers = column_numbers

    def get_param_radio_idx(self, name):
        return getattr(self, name)

    def get_param_string(self, name):
        return getattr(self, name)

    def get_param_checkbox(self, name):
        return getattr(self, name)

def render(table, colnames, drop_or_keep, select_range, column_numbers) -> ProcessResult:
    wf_module = MockWfModule(colnames, drop_or_keep, select_range, column_numbers)
    result = SelectColumns.render(wf_module, table)
    return result


class SelectColumnsTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.table = pd.DataFrame({'A': [1, 2], 'B': [2, 3], 'C': [3, 4]})

    def test_render_single_column(self):
        result = render(self.table, 'A', 1, False, '')
        self.assertEqual(result, ProcessResult(pd.DataFrame({'A': [1, 2]})))

    def test_render_strip_whitespace(self):
        result = render(self.table, 'A ', 1, False, '')
        self.assertEqual(result, ProcessResult(pd.DataFrame({'A': [1, 2]})))

    def test_render_maintain_input_column_order(self):
        result = render(self.table, 'B,A', 1, False, '')
        self.assertEqual(result, ProcessResult(
            pd.DataFrame({'A': [1, 2], 'B': [2, 3]})
        ))

    def test_render_ignore_invalid_column_name(self):
        result = render(self.table, 'A,X', 1, False, '')
        self.assertEqual(result, ProcessResult(pd.DataFrame({'A': [1, 2]})))

    def test_render_drop_columns(self):
        result = render(self.table, 'B,C', 0, False, '')
        self.assertEqual(result, ProcessResult(pd.DataFrame({'A': [1, 2]})))

    def test_render_range_input(self):
        result = render(self.table.copy(), '', 1, True, '1,3')
        self.assertEqual(result, ProcessResult(self.table[['A','C']]))

        result = render(self.table.copy(), '', 0, True, '2-3')
        self.assertEqual(result, ProcessResult(pd.DataFrame(self.table[['A']])))

        result = render(self.table.copy(), '', 0, True, '2-3,2')
        self.assertEqual(result, ProcessResult(self.table, error='There are overlapping numbers in input range'))

        result = render(self.table.copy(), '', 0, True, '2-3,giraffe')
        self.assertEqual(result, ProcessResult(self.table, error='Rows must look like "1-2", "5" or "1-2, 5"; got "giraffe"'))
