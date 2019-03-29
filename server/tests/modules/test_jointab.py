import unittest
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from cjworkbench.types import RenderColumn, TabOutput
from server.modules.jointab import render


class JoinTabTests(unittest.TestCase):
    def test_left(self):
        left = pd.DataFrame({'A': [1, 2, 3], 'B': ['x', 'y', 'z']})
        right = pd.DataFrame({'A': [1, 2], 'C': ['X', 'Y']})
        result = render(left, {
            'right_tab': TabOutput(
                'slug',
                'name',
                {'A': RenderColumn('A', 'number', '{}'),
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
        assert_frame_equal(result, pd.DataFrame({
            'A': [1, 2, 3],
            'B': ['x', 'y', 'z'],
            'C': ['X', 'Y', np.nan],
        }))

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
                 'B': RenderColumn('C', 'text', None)},
                right),
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
