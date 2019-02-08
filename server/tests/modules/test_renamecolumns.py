import pandas as pd
import unittest
from cjworkbench.types import ProcessResult
from server.modules import renamecolumns


def P(custom_list=False, rename_entries={}, list_string=''):
    return {
        'custom_list': custom_list,
        'rename-entries': rename_entries,
        'list_string': list_string,
    }


a_table = pd.DataFrame({
    'A': [1, 2],
    'B': [2, 3],
    'C': [3, 4],
})


def render(table, params):
    result = renamecolumns.render(table, params)
    result = ProcessResult.coerce(result)
    result.sanitize_in_place()
    return result


class RenameFromTableTests(unittest.TestCase):
    def test_rename_empty(self):
        # If there are no entries, return table
        params = P(custom_list=False, rename_entries={})
        result = render(a_table.copy(), params)
        self.assertEqual(result, ProcessResult(a_table))

    def test_rename_from_table(self):
        params = P(custom_list=False, rename_entries={"A": "D", "B": "A"})
        result = render(a_table.copy(), params)
        expected = ProcessResult(pd.DataFrame({
            'D': [1, 2],
            'A': [2, 3],
            'C': [3, 4],
        }))
        self.assertEqual(result, expected)

    def test_rename_custom_list_newline_separated(self):
        params = P(custom_list=True, list_string='D\nA\nC')
        result = render(a_table.copy(), params)
        expected = ProcessResult(pd.DataFrame({
            'D': [1, 2],
            'A': [2, 3],
            'C': [3, 4],
        }))
        self.assertEqual(result, expected)

    def test_rename_custom_list_comma_separated(self):
        params = P(custom_list=True, list_string='D,A,C')
        result = render(a_table.copy(), params)
        expected = ProcessResult(pd.DataFrame({
            'D': [1, 2],
            'A': [2, 3],
            'C': [3, 4],
        }))
        self.assertEqual(result, expected)

    def test_list_missing_separator(self):
        params = P(custom_list=True, list_string='D:A:C')
        result = render(a_table.copy(), params)
        self.assertEqual(
            result,
            ProcessResult(a_table, 'Separator between names not detected.')
        )

    def test_list_too_many_columns(self):
        params = P(custom_list=True, list_string='D,A,C,X')
        result = render(a_table.copy(), params)
        self.assertEqual(
            result,
            ProcessResult(
                a_table,
                'You supplied 4 column names, but the table has 3 columns'
            )
        )

    def test_list_nix_whitespace_columns(self):
        params = P(custom_list=True, list_string=',D,,A,\t,\n,C,')
        result = render(a_table.copy(), params)
        expected = ProcessResult(pd.DataFrame({
            'D': [1, 2],
            'A': [2, 3],
            'C': [3, 4],
        }))
        self.assertEqual(result, expected)

    def test_list_too_few_columns(self):
        params = P(custom_list=True, list_string='D,A')
        result = render(a_table.copy(), params)
        expected = ProcessResult(pd.DataFrame({
            'D': [1, 2],
            'A': [2, 3],
            'Column 3': [3, 4],  # TODO why not 'C'?
        }))
        self.assertEqual(result, expected)
