import io
import unittest
import pandas as pd
from server.modules.selectcolumns import SelectColumns
from server.modules.types import ProcessResult

KEEP = 1
DROP = 0


class MockWfModule:
    def __init__(self, colnames, drop_or_keep):
        self.colnames = colnames
        self.drop_or_keep = drop_or_keep

    def get_param_menu_idx(self, name):
        return getattr(self, name)

    def get_param_string(self, name):
        return getattr(self, name)


def render(table, colnames, drop_or_keep) -> ProcessResult:
    wf_module = MockWfModule(colnames, drop_or_keep)
    result = SelectColumns.render(wf_module, table)
    return result


class SelectColumnsTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.table = pd.DataFrame({'A': [1, 2], 'B': [2, 3], 'C': [3, 4]})

    def test_render_single_column(self):
        result = render(self.table, 'A', 1)
        self.assertEqual(result, ProcessResult(pd.DataFrame({'A': [1, 2]})))

    def test_render_strip_whitespace(self):
        result = render(self.table, 'A ', 1)
        self.assertEqual(result, ProcessResult(pd.DataFrame({'A': [1, 2]})))

    def test_render_maintain_input_column_order(self):
        result = render(self.table, 'B,A', 1)
        self.assertEqual(result, ProcessResult(
            pd.DataFrame({'A': [1, 2], 'B': [2, 3]})
        ))

    def test_render_ignore_invalid_column_name(self):
        result = render(self.table, 'A,X', 1)
        self.assertEqual(result, ProcessResult(pd.DataFrame({'A': [1, 2]})))

    def test_render_drop_columns(self):
        result = render(self.table, 'B,C', 0)
        self.assertEqual(result, ProcessResult(pd.DataFrame({'A': [1, 2]})))
