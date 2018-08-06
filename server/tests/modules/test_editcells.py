import json
import unittest
import pandas as pd
from pandas.testing import assert_frame_equal
from server.modules.editcells import EditCells
from server.modules.types import ProcessResult
from server.sanitizedataframe import sanitize_dataframe


class MockWfModule:
    def __init__(self, patch_json):
        self.patch_json = patch_json
        self.error = None

    def set_error(self, error):
        self.error = error

    def get_param_raw(self, param, param_type):
        if param != 'celledits':
            raise Exception('Expected param == "celledits"')
        if param_type != 'custom':
            raise Exception('Expected param_type == "custom"')

        return self.patch_json


def test_render(in_table, patch_json, out_table=pd.DataFrame(),
                out_error=''):
    wfm = MockWfModule(patch_json)
    sanitize_dataframe(in_table)

    result = ProcessResult.coerce(EditCells.render(wfm, in_table))
    result.sanitize_in_place()

    expected = ProcessResult(out_table, out_error)
    expected.sanitize_in_place()

    assert result.error == expected.error
    assert_frame_equal(result.dataframe, expected.dataframe)


class EditCellsTests(unittest.TestCase):
    def test_edit_int_to_int(self):
        test_render(
            pd.DataFrame({'A': [1, 2]}, dtype='int64'),
            json.dumps([{'row': 1, 'col': 'A', 'value': '3'}]),
            pd.DataFrame({'A': [1, 3]}, dtype='int64')
        )

    def test_edit_int_to_str(self):
        test_render(
            pd.DataFrame({'A': [1, 2]}, dtype='int64'),
            json.dumps([{'row': 1, 'col': 'A', 'value': 'foo'}]),
            pd.DataFrame({'A': ['1', 'foo']})
        )

    def test_edit_int_to_float(self):
        test_render(
            pd.DataFrame({'A': [1, 2]}, dtype='int64'),
            json.dumps([{'row': 1, 'col': 'A', 'value': '2.1'}]),
            pd.DataFrame({'A': [1, 2.1]}, dtype='float64')
        )

    def test_edit_float_to_int(self):
        # It stays float64, even though all values are int
        test_render(
            pd.DataFrame({'A': [1, 2.1]}, dtype='float64'),
            json.dumps([{'row': 1, 'col': 'A', 'value': '2'}]),
            pd.DataFrame({'A': [1, 2]}, dtype='float64')
        )

    def test_edit_float_to_str(self):
        test_render(
            pd.DataFrame({'A': [1.1, 2.1]}, dtype='float64'),
            json.dumps([{'row': 1, 'col': 'A', 'value': 'foo'}]),
            pd.DataFrame({'A': ['1.1', 'foo']})
        )

    def test_edit_str_to_int(self):
        test_render(
            pd.DataFrame({'A': ['foo', 'bar']}),
            json.dumps([{'row': 1, 'col': 'A', 'value': '2'}]),
            # All stays str
            pd.DataFrame({'A': ['foo', '2']})
        )

    def test_edit_str_category_to_new_str_category(self):
        test_render(
            pd.DataFrame({'A': ['a', 'b']}, dtype='category'),
            json.dumps([{'row': 1, 'col': 'A', 'value': 'c'}]),
            pd.DataFrame({'A': ['a', 'c']}, dtype='category')
        )

    def test_edit_str_category_to_existing_str_category(self):
        test_render(
            pd.DataFrame({'A': ['a', 'b', 'a']}, dtype='category'),
            json.dumps([{'row': 2, 'col': 'A', 'value': 'b'}]),
            pd.DataFrame({'A': ['a', 'b', 'b']}, dtype='category')
        )

    def test_two_edits_in_column(self):
        test_render(
            pd.DataFrame({'A': ['a', 'b', 'c']}),
            json.dumps([
                {'row': 1, 'col': 'A', 'value': 'x'},
                {'row': 2, 'col': 'A', 'value': 'y'},
            ]),
            pd.DataFrame({'A': ['a', 'x', 'y']})
        )

    def test_two_edits_in_row(self):
        test_render(
            pd.DataFrame({'A': ['a', 'b'], 'B': ['c', 'd']}),
            json.dumps([
                {'row': 0, 'col': 'A', 'value': 'x'},
                {'row': 0, 'col': 'B', 'value': 'y'},
            ]),
            pd.DataFrame({'A': ['x', 'b'], 'B': ['y', 'd']})
        )

    def test_empty_patch_str(self):
        test_render(
            pd.DataFrame({'A': ['a']}),
            '',
            pd.DataFrame({'A': ['a']})  # no-op
        )

    def test_empty_table(self):
        test_render(
            pd.DataFrame(),
            json.dumps([{'row': 0, 'col': 'A', 'value': 'x'}]),
            pd.DataFrame()  # no-op
        )

    def test_bad_json(self):
        test_render(
            pd.DataFrame({'A': ['a', 'b']}),
            'not JSON',
            out_error='Internal error: invalid JSON'
        )

    def test_missing_col(self):
        test_render(
            pd.DataFrame({'A': ['a', 'b']}),
            json.dumps([{'row': 0, 'col': 'B', 'value': 'x'}]),
            pd.DataFrame({'A': ['a', 'b']})  # no-op
        )

    def test_missing_row(self):
        test_render(
            pd.DataFrame({'A': ['a', 'b']}),
            json.dumps([{'row': 2, 'col': 'A', 'value': 'x'}]),
            pd.DataFrame({'A': ['a', 'b']})  # no-op
        )
