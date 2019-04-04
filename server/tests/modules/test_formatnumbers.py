import unittest
import pandas as pd
from pandas.testing import assert_frame_equal
from cjworkbench.types import RenderColumn
from server.modules.formatnumbers import render


class FormatnumbersTest(unittest.TestCase):
    def test_render_empty_is_no_op(self):
        result = render(
            pd.DataFrame({'A': [1]}),
            {'colnames': '', 'format': 'X{:d}'},
            input_columns={'A': RenderColumn('A', 'number', '{:d}')}
        )
        assert_frame_equal(result, pd.DataFrame({'A': [1]}))

    def test_render_multiple_columns(self):
        result = render(
            pd.DataFrame({'A': [1], 'B': [2], 'C': [3]}),
            {'colnames': 'A,B', 'format': 'X{:d}'},
            input_columns={
                'A': RenderColumn('A', 'number', 'A{:d}'),
                'B': RenderColumn('B', 'number', 'B{:d}'),
                'C': RenderColumn('C', 'number', 'C{:d}'),
            }
        )
        assert_frame_equal(result['dataframe'],
                           pd.DataFrame({'A': [1], 'B': [2], 'C': [3]}))
        self.assertEqual(result['column_formats'],
                         {'A': 'X{:d}', 'B': 'X{:d}'})

    def test_render_non_number_is_error(self):
        result = render(
            pd.DataFrame({'A': ['x']}),
            {'colnames': 'A', 'format': 'X{:d}'},
            input_columns={'A': RenderColumn('A', 'text', None)}
        )
        self.assertEqual(
            result,
            'Cannot format column "A" because it is of type "text".'
        )
