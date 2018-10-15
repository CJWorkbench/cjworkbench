import unittest
import numpy as np
import pandas as pd
from typing import Any, Dict, List
from pandas.testing import assert_frame_equal
from server.modules.refine import Refine, RefineSpec
from server.modules.types import ProcessResult
from .util import MockParams


def P(column: str, refine: Dict[str, Any]) -> MockParams:
    return MockParams(column=column, refine=refine)


class RefineSpecTest(unittest.TestCase):
    def _test_parse_v0(self, column: str, arr: List[Dict[str, Any]],
                       expected: RefineSpec) -> None:
        """
        Test that deprecated input is transformed into what the user expects.
        """
        result = RefineSpec.parse_v0(column, arr)
        self.assertEqual(result.renames, expected.renames)
        self.assertEqual(set(result.blacklist), set(expected.blacklist))

    def test_parse_v0_filter(self):
        self._test_parse_v0(
            'A',
            [{'type': 'select', 'column': 'A', 'content': {'value': 'foo'}}],
            RefineSpec(blacklist=['foo'])
        )

    def test_parse_v0_filter_toggle(self):
        self._test_parse_v0(
            'A',
            [
              {'type': 'select', 'column': 'A', 'content': {'value': 'foo'}},
              {'type': 'select', 'column': 'A', 'content': {'value': 'foo'}},
            ],
            RefineSpec(blacklist=[])
        )

    def test_parse_v0_filter_multiple(self):
        self._test_parse_v0(
            'A',
            [
              {'type': 'select', 'column': 'A', 'content': {'value': 'foo'}},
              {'type': 'select', 'column': 'A', 'content': {'value': 'foo'}},
            ],
            RefineSpec(blacklist=[])
        )

    def test_parse_v0_ignore_wrong_column(self):
        self._test_parse_v0(
            'A',
            [{'type': 'select', 'column': 'B', 'content': {'value': 'foo'}}],
            RefineSpec(blacklist=[])
        )

    def test_parse_v0_rename(self):
        self._test_parse_v0(
            'A',
            [
                {'type': 'change', 'column': 'A',
                 'content': {'fromVal': 'x', 'toVal': 'y'}},
            ],
            RefineSpec({'x': 'y'})
        )

    def test_parse_v0_cascade_rename(self):
        self._test_parse_v0(
            'A',
            [
                {'type': 'change', 'column': 'A',
                 'content': {'fromVal': 'x', 'toVal': 'y'}},
                {'type': 'change', 'column': 'A',
                 'content': {'fromVal': 'y', 'toVal': 'z'}},
            ],
            RefineSpec({'x': 'z', 'y': 'z'})
        )

    def test_parse_v0_blacklist_after_rename(self):
        # The old logic would run one edit at a time, modifying the dataframe
        # each time and adding a separate "selected" column. When the user
        # added a 'change', the old logic would check the 'selected' of the
        # destination value.
        #
        # ... this was a stateful and confusing way of accomplishing something
        # terribly simple: rename first, then filter.
        #
        # Unfortunately, the behavior would depend on the values in the table.
        # Now we don't: the user edits a set of instructions, not direct table
        # values. Before, in this example, 'y' might be selected or it might
        # be deselected. Now, after the upgrade, it's deselected. This isn't
        # strictly compatible, but how hard are we meant to work on supporting
        # this old format?
        self._test_parse_v0(
            'A',
            [
                {'type': 'select', 'column': 'A', 'content': {'value': 'x'}},
                {'type': 'change', 'column': 'A',
                 'content': {'fromVal': 'x', 'toVal': 'y'}},
            ],
            RefineSpec({'x': 'y'}, [])  # opinionated
        )

    def test_parse_v0_rename_remove_non_rename(self):
        self._test_parse_v0(
            'A',
            [
                {'type': 'change', 'column': 'A',
                 'content': {'fromVal': 'x', 'toVal': 'y'}},
                {'type': 'change', 'column': 'A',
                 'content': {'fromVal': 'y', 'toVal': 'x'}},
            ],
            RefineSpec({'y': 'x'})
        )

    def test_parse_v0_valueerror_bad_select_bad_value(self):
        with self.assertRaises(ValueError):
            RefineSpec.parse_v0('A', [
                {'type': 'select', 'column': 'A', 'content': {'valu': 'x'}},
            ])

    def test_parse_v0_valueerror_bad_change_bad_content_key(self):
        with self.assertRaises(ValueError):
            RefineSpec.parse_v0('A', [
                {'type': 'change', 'column': 'A',
                 'content': {'fromValx': 'x', 'toVal': 'y'}},
            ])

    def test_parse_v0_valueerror_bad_change_no_content_key(self):
        with self.assertRaises(ValueError):
            RefineSpec.parse_v0('A', [
                {'type': 'change', 'column': 'A',
                 'contentx': {'fromVal': 'x', 'toVal': 'y'}},
            ])

    def test_parse_v0_valueerror_bad_type(self):
        with self.assertRaises(ValueError):
            RefineSpec.parse_v0('A', [
                {'type': 'selec', 'column': 'A', 'content': {'value': 'x'}},
            ])

    def test_parse_v0_valueerror_not_dict(self):
        with self.assertRaises(ValueError):
            RefineSpec.parse_v0('A', ['foo'])

    def test_parse_v1_missing_renames(self):
        with self.assertRaises(ValueError):
            RefineSpec.parse('A', {'enames': {}, 'blacklist': []})

    def test_parse_v1_bad_renames(self):
        with self.assertRaises(ValueError):
            RefineSpec.parse('A', {'renames': [], 'blacklist': []})

    def test_parse_v1_bad_blacklist(self):
        with self.assertRaises(ValueError):
            RefineSpec.parse('A', {'renames': {}, 'blacklist': 3})

    def test_parse_v1(self):
        result = RefineSpec.parse('A', {
            'renames': {'x': 'y', 'y': 'z'},
            'blacklist': ['z']
        })
        self.assertEqual(result.renames, {'x': 'y', 'y': 'z'})
        self.assertEqual(result.blacklist, ['z'])

    def _test_refine_spec_apply(self, in_table: pd.DataFrame, column: str,
                                spec: RefineSpec,
                                expected_out: pd.DataFrame=pd.DataFrame(),
                                expected_error: str='') -> None:
        """Render and assert the output is as expected."""
        result = ProcessResult.coerce(spec.apply(in_table, column))
        # Sanitize result+expected, so if sanitize changes these tests may
        # break (which is what we want).
        result.sanitize_in_place()

        expected = ProcessResult(expected_out, expected_error)
        expected.sanitize_in_place()

        self.assertEqual(result.error, expected.error)
        assert_frame_equal(result.dataframe, expected.dataframe)

    def test_refine_rename_to_new(self):
        self._test_refine_spec_apply(
            pd.DataFrame({'A': ['a', 'b']}),
            'A',
            RefineSpec({'b': 'c'}),
            pd.DataFrame({'A': ['a', 'c']}, dtype='category')
        )

    def test_refine_rename_category_to_new(self):
        self._test_refine_spec_apply(
            pd.DataFrame({'A': ['a', 'b']}, dtype='category'),
            'A',
            RefineSpec({'b': 'c'}),
            pd.DataFrame({'A': ['a', 'c']}, dtype='category')
        )

    def test_refine_rename_category_to_existing(self):
        self._test_refine_spec_apply(
            pd.DataFrame({'A': ['a', 'b']}, dtype='category'),
            'A',
            RefineSpec({'b': 'a'}),
            pd.DataFrame({'A': ['a', 'a']}, dtype='category')
        )

    def test_refine_rename_swap(self):
        self._test_refine_spec_apply(
            pd.DataFrame({'A': ['a', 'b']}, dtype='category'),
            'A',
            RefineSpec({'a': 'b', 'b': 'a'}),
            pd.DataFrame({'A': ['b', 'a']}, dtype='category')
        )

    def test_refine_blacklist(self):
        self._test_refine_spec_apply(
            pd.DataFrame({'A': ['a', 'b']}, dtype='category'),
            'A',
            RefineSpec({}, ['a']),
            pd.DataFrame({'A': ['b']}, dtype='category')
        )

    def test_refine_cast_int_to_str(self):
        self._test_refine_spec_apply(
            pd.DataFrame({'A': [1, 2]}),
            'A',
            RefineSpec({'1': '2'}),
            pd.DataFrame({'A': ['2', '2']}, dtype='category')
        )

    def test_refine_cast_date_to_str(self):
        self._test_refine_spec_apply(
            pd.DataFrame({'A': [np.datetime64('2018-08-03T17:12')]}),
            'A',
            RefineSpec({'2018-08-03 17:12:00': 'x'}),
            pd.DataFrame({'A': ['x']}, dtype='category')
        )

    def _test_render(self, in_table: pd.DataFrame, column: str,
                     edits_json: Dict[str, Any],
                     expected_out: pd.DataFrame=pd.DataFrame(),
                     expected_error: str='') -> None:
        """Test that the render method works (kinda an integration test)."""
        params = P(column, edits_json)
        result = Refine.render(params, in_table)
        result.sanitize_in_place()

        expected = ProcessResult(expected_out, expected_error)
        expected.sanitize_in_place()

        self.assertEqual(result.error, expected.error)
        assert_frame_equal(result.dataframe, expected.dataframe)

    def test_render_no_column_is_no_op(self):
        self._test_render(
            pd.DataFrame({'A': ['b']}, dtype='category'),
            {},
            {'renames': {}, 'blacklist': []},
            pd.DataFrame({'A': ['b']}, dtype='category')
        )

    def test_render_no_json_is_no_op(self):
        self._test_render(
            pd.DataFrame({'A': ['b']}, dtype='category'),
            'A',
            {},
            pd.DataFrame({'A': ['b']}, dtype='category')
        )

    def test_render_parse_v0(self):
        self._test_render(
            pd.DataFrame({'A': ['a', 'b']}, dtype='category'),
            'A',
            [
                {'type': 'change', 'column': 'A',
                 'content': {'fromVal': 'a', 'toVal': 'c'}},
                {'type': 'select', 'column': 'A', 'content': {'value': 'b'}},
            ],
            pd.DataFrame({'A': ['c']}, dtype='category')
        )

    def test_render_parse_v1(self):
        self._test_render(
            pd.DataFrame({'A': ['a', 'b']}, dtype='category'),
            'A',
            {'renames': {'a': 'c'}, 'blacklist': ['b']},
            pd.DataFrame({'A': ['c']}, dtype='category')
        )

    def test_render_parse_error(self):
        self._test_render(
            pd.DataFrame({'A': ['a', 'b']}, dtype='category'),
            'A',
            {'renames': ['foo', 'bar'], 'blacklist': 4},
            pd.DataFrame(),
            'Internal error: "renames" must be a dict from old value to new'
        )
