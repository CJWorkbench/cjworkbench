import unittest
import pandas as pd
from server.modules.duplicatecolumn import DuplicateColumn
from server.modules.types import ProcessResult


class MockWfModule:
    def __init__(self, colnames):
        self.colnames = colnames

    def get_param_string(self, x):
        return self.colnames


def render(wf_module, table):
    result = DuplicateColumn.render(wf_module, table)
    result = ProcessResult.coerce(result)
    result.sanitize_in_place()  # important: duplicate makes colname conflicts
    return result


class DuplicateColumnTests(unittest.TestCase):
    def test_duplicate_column(self):
        table = pd.DataFrame({
            'A': [1, 2],
            'B': [2, 3],
            'C': [3, 4],
        })
        wf_module = MockWfModule('A,C')
        result = render(wf_module, table)

        expected = ProcessResult(pd.DataFrame({
            'A': [1, 2],
            'Copy of A': [1, 2],
            'B': [2, 3],
            'C': [3, 4],
            'Copy of C': [3, 4],
        }))
        self.assertEqual(result, expected)

    def test_duplicate_with_existing(self):
        table = pd.DataFrame({
            'A': [1, 2],
            'Copy of A': [2, 3],
            'Copy of A 1': [3, 4],
            'C': [4, 5],
        })
        wf_module = MockWfModule('A')
        result = render(wf_module, table)

        expected = ProcessResult(pd.DataFrame({
            'A': [1, 2],
            'Copy of A 2': [1, 2],
            'Copy of A': [2, 3],
            'Copy of A 1': [3, 4],
            'C': [4, 5],
        }))
        self.assertEqual(result, expected)
