import json
import unittest
from typing import Any, Dict, List
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from refine import render, migrate_params, RefineSpec


def P(column: str, refine: Dict[str, Any]) -> Dict[str, Any]:
    return {"column": column, "refine": refine}


class MigrateParamsTest(unittest.TestCase):
    def _test_parse_v0(
        self, column: str, arr: List[Dict[str, Any]], expected: RefineSpec
    ) -> None:
        """
        Test that deprecated input is transformed into what the user expects.
        """
        result = migrate_params({"column": column, "refine": json.dumps(arr)})
        self.assertEqual(result["column"], column)
        refine = result["refine"]
        self.assertEqual(refine["renames"], expected.renames)

    # v0 blacklist values ignored
    def test_parse_v0_filter(self):
        self._test_parse_v0(
            "A",
            [{"type": "select", "column": "A", "content": {"value": "foo"}}],
            RefineSpec(),
        )

    def test_parse_v0_filter_toggle(self):
        self._test_parse_v0(
            "A",
            [
                {"type": "select", "column": "A", "content": {"value": "foo"}},
                {"type": "select", "column": "A", "content": {"value": "foo"}},
            ],
            RefineSpec(),
        )

    def test_parse_v0_filter_multiple(self):
        self._test_parse_v0(
            "A",
            [
                {"type": "select", "column": "A", "content": {"value": "foo"}},
                {"type": "select", "column": "A", "content": {"value": "foo"}},
            ],
            RefineSpec(),
        )

    def test_parse_v0_ignore_wrong_column(self):
        self._test_parse_v0(
            "A",
            [{"type": "select", "column": "B", "content": {"value": "foo"}}],
            RefineSpec(),
        )

    def test_parse_v0_rename(self):
        self._test_parse_v0(
            "A",
            [
                {
                    "type": "change",
                    "column": "A",
                    "content": {"fromVal": "x", "toVal": "y"},
                }
            ],
            RefineSpec({"x": "y"}),
        )

    def test_parse_v0_cascade_rename(self):
        self._test_parse_v0(
            "A",
            [
                {
                    "type": "change",
                    "column": "A",
                    "content": {"fromVal": "x", "toVal": "y"},
                },
                {
                    "type": "change",
                    "column": "A",
                    "content": {"fromVal": "y", "toVal": "z"},
                },
            ],
            RefineSpec({"x": "z", "y": "z"}),
        )

    def test_parse_v0_no_blacklist_after_rename(self):
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

        # UPDATE 1/29/2019
        # New Refine module does not filter and therefore does not make use of the blacklist.
        # blacklist now omitted from RefineSpec, so only rename should be included
        self._test_parse_v0(
            "A",
            [
                {"type": "select", "column": "A", "content": {"value": "x"}},
                {
                    "type": "change",
                    "column": "A",
                    "content": {"fromVal": "x", "toVal": "y"},
                },
            ],
            RefineSpec({"x": "y"}),  # opinionated
        )

    def test_parse_v0_rename_remove_non_rename(self):
        self._test_parse_v0(
            "A",
            [
                {
                    "type": "change",
                    "column": "A",
                    "content": {"fromVal": "x", "toVal": "y"},
                },
                {
                    "type": "change",
                    "column": "A",
                    "content": {"fromVal": "y", "toVal": "x"},
                },
            ],
            RefineSpec({"y": "x"}),
        )

    def test_parse_v0_valueerror_bad_select_bad_value(self):
        with self.assertRaises(ValueError):
            migrate_params(
                {
                    "column": "A",
                    "refine": json.dumps(
                        [{"type": "select", "column": "A", "content": {"valu": "x"}}]
                    ),
                }
            )

    def test_parse_v0_valueerror_bad_change_bad_content_key(self):
        with self.assertRaises(ValueError):
            migrate_params(
                {
                    "column": "A",
                    "refine": json.dumps(
                        [
                            {
                                "type": "change",
                                "column": "A",
                                "content": {"fromValx": "x", "toVal": "y"},
                            }
                        ]
                    ),
                }
            )

    def test_parse_v0_valueerror_bad_change_no_content_key(self):
        with self.assertRaises(ValueError):
            migrate_params(
                {
                    "column": "A",
                    "refine": json.dumps(
                        [
                            {
                                "type": "change",
                                "column": "A",
                                "contentx": {"fromVal": "x", "toVal": "y"},
                            }
                        ]
                    ),
                }
            )

    def test_parse_v0_valueerror_bad_type(self):
        with self.assertRaises(ValueError):
            migrate_params(
                {
                    "column": "A",
                    "refine": json.dumps(
                        [{"type": "selec", "column": "A", "content": {"value": "x"}}]
                    ),
                }
            )

    def test_parse_v0_valueerror_not_dict(self):
        with self.assertRaises(ValueError):
            migrate_params({"column": "A", "refine": json.dumps("A")})

    def test_parse_v1(self):
        result = migrate_params(
            {"column": "A", "refine": '{"renames": {"a": "b"}, "blacklist": []}'}
        )
        self.assertEqual(result, {"column": "A", "refine": {"renames": {"a": "b"}}})

    def test_parse_v1_empty_refine(self):
        result = migrate_params({"column": "A", "refine": ""})
        self.assertEqual(result, {"column": "A", "refine": {"renames": {}}})

    def _test_parse_v2(
        self, column: str, arr: Dict[str, Any], expected: RefineSpec
    ) -> None:
        result = migrate_params({"column": column, "refine": arr})
        self.assertEqual(result["column"], column)
        refine = result["refine"]
        self.assertEqual(refine["renames"], expected.renames)
        self.assertTrue("blackist" not in refine)
        self.assertEqual(len(refine.keys()), 1)

    def test_parse_v2_no_blacklist_after_rename(self):
        self._test_parse_v2(
            "A", {"renames": {"a": "b"}, "blacklist": ["c"]}, RefineSpec({"a": "b"})
        )

    def test_parse_v3_only_rename(self):
        self._test_parse_v2("A", {"renames": {"a": "b"}}, RefineSpec({"a": "b"}))

    def _test_refine_spec_apply(
        self,
        in_table: pd.DataFrame,
        column: str,
        spec: RefineSpec,
        expected_out: pd.DataFrame = pd.DataFrame(),
        expected_error: str = "",
    ) -> None:
        """Render and assert the output is as expected."""
        result = spec.apply(in_table, column)

        if not expected_out.empty and expected_error:
            table, error = result
            self.assertEqual(error, expected_error)
            assert_frame_equal(table, expected_out)
        elif expected_error:
            self.assertEqual(result, expected_error)
        else:
            assert_frame_equal(result, expected_out)

    def test_refine_rename_to_new(self):
        self._test_refine_spec_apply(
            pd.DataFrame({"A": ["a", "b"]}),
            "A",
            RefineSpec({"b": "c"}),
            pd.DataFrame({"A": ["a", "c"]}, dtype="category"),
        )

    def test_refine_rename_category_to_new(self):
        self._test_refine_spec_apply(
            pd.DataFrame({"A": ["a", "b"]}, dtype="category"),
            "A",
            RefineSpec({"b": "c"}),
            pd.DataFrame({"A": ["a", "c"]}, dtype="category"),
        )

    def test_refine_spurious_rename(self):
        self._test_refine_spec_apply(
            pd.DataFrame({"A": ["a"]}, dtype="category"),
            "A",
            RefineSpec({"b": "c"}),
            pd.DataFrame({"A": ["a"]}, dtype="category"),
        )

    def test_refine_rename_empty_category(self):
        self._test_refine_spec_apply(
            pd.DataFrame({"A": []}, dtype="category"),
            "A",
            RefineSpec({"b": "c"}),
            pd.DataFrame({"A": []}, dtype="category"),
        )

    def test_refine_rename_nan_category(self):
        # Get explicit, because pandas botches the comparison:
        #
        # >>> self._test_refine_spec_apply(
        #     pd.DataFrame({'A': [np.nan]}, dtype='category'),
        #     'A', RefineSpec({'b': 'c'}),
        #     pd.DataFrame({'A': [np.nan]}, dtype='category')
        # )
        # Attribute "dtype" are different
        # [left]:  CategoricalDtype(categories=[], ordered=False)
        # [right]: CategoricalDtype(categories=[], ordered=False)
        spec = RefineSpec({"b": "c"})
        result = spec.apply(pd.DataFrame({"A": []}, dtype="category"), "A")
        self.assertEqual(0, len(result))
        self.assertEqual(0, len(result["A"].cat.categories))

    def test_refine_rename_category_to_existing(self):
        self._test_refine_spec_apply(
            pd.DataFrame({"A": ["a", "b"]}, dtype="category"),
            "A",
            RefineSpec({"b": "a"}),
            pd.DataFrame({"A": ["a", "a"]}, dtype="category"),
        )

    def test_refine_ignore_nan(self):
        self._test_refine_spec_apply(
            pd.DataFrame({"A": ["a", "b", np.nan]}, dtype="category"),
            "A",
            RefineSpec({"b": "a"}),
            pd.DataFrame({"A": ["a", "a", np.nan]}, dtype="category"),
        )

    def test_refine_rename_swap(self):
        self._test_refine_spec_apply(
            pd.DataFrame({"A": ["a", "b"]}, dtype="category"),
            "A",
            RefineSpec({"a": "b", "b": "a"}),
            pd.DataFrame({"A": ["b", "a"]}, dtype="category"),
        )

    def _test_render(
        self,
        in_table: pd.DataFrame,
        column: str,
        edits_json: Dict[str, Any],
        expected_out: pd.DataFrame = pd.DataFrame(),
        expected_error: str = "",
    ) -> None:
        """Test that the render method works (kinda an integration test)."""
        params = P(column, edits_json)
        result = render(in_table, params)

        if not expected_out.empty and expected_error:
            table, error = result
            self.assertEqual(error, expected_error)
            assert_frame_equal(table, expected_out)
        elif expected_error:
            self.assertEqual(result, expected_error)
        else:
            assert_frame_equal(result, expected_out)

    def test_render_no_column_is_no_op(self):
        self._test_render(
            pd.DataFrame({"A": ["b"]}, dtype="category"),
            {},
            {"renames": {}},
            pd.DataFrame({"A": ["b"]}, dtype="category"),
        )

    def test_render_no_json_is_no_op(self):
        self._test_render(
            pd.DataFrame({"A": ["b"]}, dtype="category"),
            "A",
            {},
            pd.DataFrame({"A": ["b"]}, dtype="category"),
        )
