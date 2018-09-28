import io
import json
import numpy as np
import pandas as pd
import unittest
from server.modules.rename import RenameFromTable
from server.modules.types import ProcessResult

a_table = pd.DataFrame({
    'A': [1, 2],
    'B': [2, 3],
    'C': [3, 4],
})


class MockWfModule:
    def __init__(self, custom_list=False, rename_entries='', list_string=''):
        self.custom_list = custom_list
        self.rename_entries = rename_entries
        self.list_string = list_string

    def get_param_string(self, _):
        return self.list_string

    def get_param_checkbox(self, _):
        return self.custom_list

    def get_param_raw(self, _, __):
        return self.rename_entries


def render(wf_module, table):
    result = RenameFromTable.render(wf_module, table)
    result = ProcessResult.coerce(result)
    result.sanitize_in_place()
    return result


class RenameFromTableTests(unittest.TestCase):
    def test_rename_empty_str(self):
        # Should only happen when a module is first created. Return table
        wf_module = MockWfModule(rename_entries='')
        result = render(wf_module, a_table.copy())
        self.assertEqual(result, ProcessResult(a_table))

    def test_rename_empty(self):
        # If there are no entries, return table
        wf_module = MockWfModule(custom_list=False, rename_entries='{}')
        result = render(wf_module, a_table.copy())
        self.assertEqual(result, ProcessResult(a_table))

    def test_rename_from_table(self):
        wf_module = MockWfModule(custom_list=False,
                                 rename_entries='{"A": "D", "B": "A"}')
        result = render(wf_module, a_table.copy())
        expected = ProcessResult(pd.DataFrame({
            'D': [1, 2],
            'A': [2, 3],
            'C': [3, 4],
        }))
        self.assertEqual(result, expected)

    def test_rename_custom_list_newline_separated(self):
        wf_module = MockWfModule(custom_list=True, list_string='D\nA\nC')
        result = render(wf_module, a_table.copy())
        expected = ProcessResult(pd.DataFrame({
            'D': [1, 2],
            'A': [2, 3],
            'C': [3, 4],
        }))
        self.assertEqual(result, expected)

    def test_rename_custom_list_comma_separated(self):
        wf_module = MockWfModule(custom_list=True, list_string='D,A,C')
        result = render(wf_module, a_table.copy())
        expected = ProcessResult(pd.DataFrame({
            'D': [1, 2],
            'A': [2, 3],
            'C': [3, 4],
        }))
        self.assertEqual(result, expected)

    def test_list_missing_separator(self):
        wf_module = MockWfModule(custom_list=True, list_string='D:A:C')
        result = render(wf_module, a_table.copy())
        self.assertEqual(
            result,
            ProcessResult(a_table, 'Separator between names not detected.')
        )

    def test_list_too_many_columns(self):
        wf_module = MockWfModule(custom_list=True, list_string='D,A,C,X')
        result = render(wf_module, a_table.copy())
        self.assertEqual(
            result,
            ProcessResult(
                a_table,
                'You supplied 4 column names, but the table has 3 columns'
            )
        )

    def test_list_nix_whitespace_columns(self):
        wf_module = MockWfModule(custom_list=True,
                                 list_string=',D,,A,\t,\n,C,')
        result = render(wf_module, a_table.copy())
        expected = ProcessResult(pd.DataFrame({
            'D': [1, 2],
            'A': [2, 3],
            'C': [3, 4],
        }))
        self.assertEqual(result, expected)

    def test_list_too_few_columns(self):
        wf_module = MockWfModule(custom_list=True, list_string='D,A')
        result = render(wf_module, a_table.copy())
        expected = ProcessResult(pd.DataFrame({
            'D': [1, 2],
            'A': [2, 3],
            'C': [3, 4],
        }))
