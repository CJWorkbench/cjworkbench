from dataclasses import dataclass
from typing import Optional
import unittest
import pandas as pd
from pandas.testing import assert_frame_equal
from server.modules.renamecolumns import migrate_params, render, \
        _parse_renames, _parse_custom_list


def P(custom_list=False, renames={}, list_string=''):
    return {
        'custom_list': custom_list,
        'renames': renames,
        'list_string': list_string,
    }


@dataclass
class Column:
    format: Optional[str] = None


a_table = pd.DataFrame({
    'A': [1, 2],
    'B': [2, 3],
    'C': [3, 4],
})


class MigrateParamsTests(unittest.TestCase):
    def test_v0_empty_rename_entries(self):
        result = migrate_params({
            'custom_list': False,
            'list_string': 'A\nB\nC',
            'rename-entries': '',
        })
        self.assertEqual(result, {
            'custom_list': False,
            'list_string': 'A\nB\nC',
            'renames': {},
        })

    def test_v0(self):
        result = migrate_params({
            'custom_list': False,
            'list_string': 'A\nB\nC',
            'rename-entries': '{"A":"B","B":"C"}',
        })
        self.assertEqual(result, {
            'custom_list': False,
            'list_string': 'A\nB\nC',
            'renames': {'A': 'B', 'B': 'C'},
        })

    def test_v1(self):
        result = migrate_params({
            'custom_list': False,
            'list_string': 'A\nB\nC',
            'renames': {'A': 'B', 'B': 'C'},
        })
        self.assertEqual(result, {
            'custom_list': False,
            'list_string': 'A\nB\nC',
            'renames': {'A': 'B', 'B': 'C'},
        })


class RenderTests(unittest.TestCase):
    def test_parse_renames_ignore_missing_columns(self):
        self.assertEqual(
            _parse_renames({'A': 'B', 'C': 'D'}, ['A', 'X']),
            {'A': 'B'}
        )

    def test_parse_renames_swap(self):
        self.assertEqual(
            _parse_renames({'A': 'B', 'B': 'C', 'C': 'A'}, ['A', 'B', 'C']),
            {'A': 'B', 'B': 'C', 'C': 'A'}
        )

    def test_parse_renames_avoid_duplicates(self):
        self.assertEqual(
            _parse_renames({'A': 'B', 'C': 'B'}, ['A', 'B', 'C']),
            {'A': 'B', 'B': 'B 1', 'C': 'B 2'}
        )

    def test_parse_custom_list_by_newline(self):
        self.assertEqual(
            _parse_custom_list('X\nY\nZ', ['A', 'B', 'C']),
            {'A': 'X', 'B': 'Y', 'C': 'Z'}
        )

    def test_parse_custom_list_by_comma(self):
        self.assertEqual(
            _parse_custom_list('X, Y, Z', ['A', 'B', 'C']),
            {'A': 'X', 'B': 'Y', 'C': 'Z'}
        )

    def test_parse_custom_list_newline_means_ignore_commas(self):
        self.assertEqual(
            _parse_custom_list('X,Y\nZ,A\nB,C', ['A', 'B', 'C']),
            {'A': 'X,Y', 'B': 'Z,A', 'C': 'B,C'}
        )

    def test_parse_custom_list_trailing_newline_still_split_by_comma(self):
        """If the user added a newline to the end, it's still commas."""
        self.assertEqual(
            _parse_custom_list('X, Y, Z\n', ['A', 'B', 'C']),
            {'A': 'X', 'B': 'Y', 'C': 'Z'}
        )

    def test_parse_custom_list_allow_too_few_columns(self):
        self.assertEqual(
            _parse_custom_list('X\nY', ['A', 'B', 'C']),
            {'A': 'X', 'B': 'Y'}
        )

    def test_parse_custom_list_ignore_no_op_renames(self):
        self.assertEqual(
            _parse_custom_list('A\nY\nC', ['A', 'B', 'C']),
            {'B': 'Y'}
        )

    def test_parse_custom_list_too_many_columns_is_valueerror(self):
        with self.assertRaisesRegex(
            ValueError,
            'You supplied 4 column names, but the table has 3 columns.'
        ):
            _parse_custom_list('A\nB\nC\nD', ['A', 'B', 'C'])

    def test_parse_custom_list_ignore_trailing_newline(self):
        self.assertEqual(
            _parse_custom_list('X\nY\n', ['A', 'B']),
            {'A': 'X', 'B': 'Y'}  # no ValueError
        )

    def test_parse_custom_list_skip_whitespace_columns(self):
        self.assertEqual(
            _parse_custom_list('X\n\nZ', ['A', 'B', 'C']),
            {'A': 'X', 'C': 'Z'}
        )

    def test_rename_empty_is_no_op(self):
        table = pd.DataFrame({'A': ['x']})
        result = render(table, P(custom_list=False, renames={}),
                        input_columns={'A': Column()})
        assert_frame_equal(result, pd.DataFrame({'A': ['x']}))

    def test_rename_custom_list_empty_is_no_op(self):
        table = pd.DataFrame({'A': ['x']})
        result = render(table, P(custom_list=True, list_string=''),
                        input_columns={'A': Column()})
        assert_frame_equal(result, pd.DataFrame({'A': ['x']}))

    def test_rename_custom_list_too_many_columns_is_error(self):
        table = pd.DataFrame({'A': ['x']})
        result = render(table, P(custom_list=True, list_string='X,Y'),
                        input_columns={'A': Column()})
        self.assertEqual(
            result, 
            'You supplied 2 column names, but the table has 1 columns.'
        )

    def test_rename_formats(self):
        table = pd.DataFrame({'A': ['x'], 'B': [1]})
        result = render(
            table,
            P(custom_list=False, renames={'A': 'X', 'B': 'Y'}),
            input_columns={'A': Column(), 'B': Column('{:,d}')}
        )
        assert_frame_equal(result['dataframe'],
                           pd.DataFrame({'X': ['x'], 'Y': [1]}))
        self.assertEqual(result['column_formats'], {'Y': '{:,d}', 'X': None})

    def test_rename_swap_columns(self):
        table = pd.DataFrame({'A': ['x'], 'B': [1]})
        result = render(
            table,
            P(custom_list=False, renames={'A': 'B', 'B': 'A'}),
            input_columns={'A': Column(), 'B': Column('{:,d}')}
        )
        assert_frame_equal(result['dataframe'],
                           pd.DataFrame({'B': ['x'], 'A': [1]}))
        self.assertEqual(result['column_formats'], {'A': '{:,d}', 'B': None})

    def test_custom_list(self):
        table = pd.DataFrame({'A': ['x'], 'B': [1]})
        result = render(
            table,
            P(custom_list=True, list_string='X\nY'),
            input_columns={'A': Column(), 'B': Column('{:,d}')}
        )
        assert_frame_equal(result['dataframe'],
                           pd.DataFrame({'X': ['x'], 'Y': [1]}))
        self.assertEqual(result['column_formats'], {'Y': '{:,d}', 'X': None})

    def test_dict_disallow_rename_to_null(self):
        table = pd.DataFrame({'A': [1]})
        result = render(table, P(renames={'A': ''}),
                        input_columns={'A': Column()})
        assert_frame_equal(result, pd.DataFrame({'A': [1]}))

    def test_custom_list_disallow_rename_to_null(self):
        table = pd.DataFrame({'A': [1], 'B': [2], 'C': [3]})
        result = render(table, P(custom_list=True, list_string='D\n\nF'),
                        input_columns={'A': Column(), 'B': Column(), 'C':
                                       Column()})
        assert_frame_equal(result['dataframe'],
                           pd.DataFrame({'D': [1], 'B': [2], 'F': [3]}))
