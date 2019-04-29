import unittest
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from cjworkbench.types import RenderColumn, TabOutput
from server.modules.jointab import render


class JoinTabTests(unittest.TestCase):
    def test_left(self):
        left = pd.DataFrame({'A': [1, 2, 3], 'B': ['x', 'y', 'z']})
        right = pd.DataFrame({'A': [1, 2], 'C': ['X', 'Y'], 'D': [0.1, 0.2]})
        result = render(left, {
            'right_tab': TabOutput(
                'slug',
                'name',
                {'A': RenderColumn('A', 'number', '{:,.2f}'),
                 'C': RenderColumn('C', 'text', None),
                 'D': RenderColumn('D', 'number', '{:,}')},
                right),
            'join_columns': {
                'on': 'A',
                'right': 'C,D',
            },
            'type': 0,
        }, input_columns={
            'A': RenderColumn('A', 'number', '{:d}'),
            'B': RenderColumn('B', 'text', None),
        })
        assert_frame_equal(result['dataframe'], pd.DataFrame({
            'A': [1, 2, 3],
            'B': ['x', 'y', 'z'],
            'C': ['X', 'Y', np.nan],
            'D': [0.1, 0.2, np.nan],
        }))
        self.assertEqual(result['column_formats'], {'C': None, 'D': '{:,}'})

    def test_on_types_differ(self):
        left = pd.DataFrame({'A': [1, 2, 3], 'B': ['x', 'y', 'z']})
        right = pd.DataFrame({'A': ['1', '2'], 'C': ['X', 'Y']})
        result = render(left, {
            'right_tab': TabOutput(
                'slug',
                'Tab 2',
                {'A': RenderColumn('A', 'text', None),
                 'C': RenderColumn('C', 'text', None)},
                right),
            'join_columns': {
                'on': 'A',
                'right': 'C',
            },
            'type': 0,
        }, input_columns={
            'A': RenderColumn('A', 'number', '{}'),
            'B': RenderColumn('B', 'text', None),
        })

        self.assertEqual(result, (
            'Column "A" is *number* in this tab and *text* in Tab 2. '
            'Please convert one or the other so they are both the same type.'
        ))

    def test_prevent_overwrite(self):
        left = pd.DataFrame({'A': [1, 2, 3], 'B': ['x', 'y', 'z']})
        right = pd.DataFrame({'A': ['1', '2'], 'B': ['X', 'Y']})
        result = render(left, {
            'right_tab': TabOutput(
                'slug',
                'Tab 2',
                {'A': RenderColumn('A', 'number', '{}'),
                 'B': RenderColumn('B', 'text', None)},
                right
            ),
            'join_columns': {
                'on': 'A',
                'right': 'B',
            },
            'type': 0,
        }, input_columns={
            'A': RenderColumn('A', 'number', '{}'),
            'B': RenderColumn('B', 'text', None),
        })

        self.assertEqual(result, (
            'You tried to add "B" from Tab 2, but your table already has that '
            'column. Please rename the column in one of the tabs, or unselect '
            'the column.'
        ))

    def test_left_join_delete_unused_categories_in_added_columns(self):
        left = pd.DataFrame({'A': ['a', 'b']}, dtype='category')
        right = pd.DataFrame({
            'A': pd.Series(['a', 'z'], dtype='category'),
            'B': pd.Series(['x', 'y'], dtype='category'),
        })
        result = render(left, {
            'right_tab': TabOutput(
                'slug',
                'Tab 2',
                {'A': RenderColumn('A', 'text', None),
                 'B': RenderColumn('B', 'text', None)},
                right
            ),
            'join_columns': {'on': 'A', 'right': 'B'},
            'type': 0,
        }, input_columns={
            'A': RenderColumn('A', 'text', None),
        })
        # 'z' category does not appear in result, so it should not be a
        # category in the 'B' column.
        assert_frame_equal(result['dataframe'], pd.DataFrame({
            'A': pd.Series(['a', 'b'], dtype='category'),
            'B': pd.Series(['x', np.nan], dtype='category')
        }))

    def test_right_join_delete_unused_categories_in_input_columns(self):
        left = pd.DataFrame({
            'A': pd.Series(['a', 'b'], dtype='category'),  # join column
            'B': pd.Series(['c', 'd'], dtype='category'),  # other column
        })
        right = pd.DataFrame({
            'A': pd.Series(['a'], dtype='category'),  # join column
            'C': ['e'],
        })
        result = render(left, {
            'right_tab': TabOutput(
                'slug',
                'Tab 2',
                {'A': RenderColumn('A', 'text', None),
                 'C': RenderColumn('C', 'text', None)},
                right
            ),
            'join_columns': {'on': 'A', 'right': 'C'},
            'type': 2,
        }, input_columns={
            'A': RenderColumn('A', 'text', None),
            'B': RenderColumn('B', 'text', None),
        })
        # 'b' and 'd' categories don't appear in result, so it should not be
        # categories in the result dataframe.
        assert_frame_equal(result['dataframe'], pd.DataFrame({
            'A': pd.Series(['a'], dtype='category'),
            'B': pd.Series(['c'], dtype='category'),
            'C': ['e']
        }))

    def test_inner_join_delete_unused_categories_in_all_columns(self):
        left = pd.DataFrame({
            'A': pd.Series(['a', 'b'], dtype='category'),  # join column
            'B': pd.Series(['c', 'd'], dtype='category'),  # other column
        })
        right = pd.DataFrame({
            'A': pd.Series(['a', 'x'], dtype='category'),  # join column
            'C': pd.Series(['e', 'y'], dtype='category'),  # other column
        })
        result = render(left, {
            'right_tab': TabOutput(
                'slug',
                'Tab 2',
                {'A': RenderColumn('A', 'text', None),
                 'C': RenderColumn('C', 'text', None)},
                right
            ),
            'join_columns': {'on': 'A', 'right': 'C'},
            'type': 1,
        }, input_columns={
            'A': RenderColumn('A', 'text', None),
            'B': RenderColumn('B', 'text', None),
        })
        # 'b', 'd', 'x' and 'y' categories don't appear in the result, so the
        # dtypes should not contain them.
        assert_frame_equal(result['dataframe'], pd.DataFrame({
            'A': ['a'],
            'B': ['c'],
            'C': ['e'],
        }, dtype='category'))
