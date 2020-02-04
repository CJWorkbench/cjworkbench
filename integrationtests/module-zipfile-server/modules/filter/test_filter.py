import unittest
from typing import Any, Dict
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from filter import render, migrate_params


def simple_params(
    colname: str,
    condition: str,
    value: str,
    case_sensitive: bool = False,
    keep: bool = True,
) -> Dict[str, Any]:
    return {
        "keep": keep,
        "filters": {
            "operator": "and",
            "filters": [
                {
                    "operator": "and",
                    "subfilters": [
                        {
                            "colname": colname,
                            "condition": condition,
                            "value": value,
                            "case_sensitive": case_sensitive,
                        }
                    ],
                }
            ],
        },
    }


class TestMigrateParams(unittest.TestCase):
    def test_v0_select_stays_select(self):
        self.assertEqual(
            migrate_params(
                {
                    "column": "A",
                    "condition": 0,  # "Select" (the default)
                    "value": "value",
                    "casesensitive": False,
                    "keep": 0,  # "Keep"
                    "regex": False,
                }
            ),
            simple_params("A", "", "value"),
        )

    def test_v0_text_contains_without_regex_stays_text_contains(self):
        self.assertEqual(
            migrate_params(
                {
                    "column": "A",
                    "condition": 2,  # "Text contains"
                    "value": "value",
                    "casesensitive": False,
                    "keep": 0,  # "Keep"
                    "regex": False,
                }
            ),
            simple_params("A", "text_contains", "value"),
        )

    def test_v0_text_contains_regex_changes_condition(self):
        self.assertEqual(
            migrate_params(
                {
                    "column": "A",
                    "condition": 2,  # "Text contains"
                    "value": "value",
                    "casesensitive": False,
                    "keep": 0,  # "Keep"
                    "regex": True,
                }
            ),
            simple_params("A", "text_contains_regex", "value"),
        )

    def test_v0_cell_is_empty_changes_number(self):
        self.assertEqual(
            migrate_params(
                {
                    "column": "A",
                    "condition": 6,  # "Cell is empty"
                    "value": "value",
                    "casesensitive": False,
                    "keep": 0,  # "Keep"
                    "regex": True,
                }
            ),
            simple_params("A", "cell_is_empty", "value"),
        )

    def test_v0_from_dropdown(self):
        self.assertEqual(migrate_params({"column": "A"}), simple_params("A", "", ""))

    def test_v2_keep_0_means_true(self):
        self.assertEqual(
            migrate_params({"keep": 0, "filters": {"operator": "and", "filters": []}}),
            {"keep": True, "filters": {"operator": "and", "filters": []}},
        )

    def test_v2_keep_1_means_false(self):
        self.assertEqual(
            migrate_params({"keep": 1, "filters": {"operator": "and", "filters": []}}),
            {"keep": False, "filters": {"operator": "and", "filters": []}},
        )

    def test_v3(self):
        self.assertEqual(
            migrate_params(
                {"keep": True, "filters": {"operator": "and", "filters": []}}
            ),
            {"keep": True, "filters": {"operator": "and", "filters": []}},
        )


class TestRender(unittest.TestCase):
    def setUp(self):
        # Test data includes some partially and completely empty rows because
        # this tends to freak out Pandas
        self.table = pd.DataFrame(
            [
                ["fred", 2, 3, "round", "2018-1-12"],
                ["frederson", 5, np.nan, "square", "2018-1-12 08:15"],
                [np.nan, np.nan, np.nan, np.nan, np.nan],
                ["maggie", 8, 10, "Round", "2015-7-31"],
                ["Fredrick", 5, np.nan, "square", "2018-3-12"],
            ],
            columns=["a", "b", "c", "d", "date"],
        )

    def test_no_column(self):
        params = simple_params("", "text_contains", "fred")
        result = render(self.table, params)
        assert_frame_equal(result, self.table)

    def test_no_value(self):
        params = simple_params("a", "text_contains", "")
        result = render(self.table, params)
        assert_frame_equal(result, self.table)

    def test_illegal_condition(self):
        params = simple_params("a", "", "value")
        result = render(self.table, params)
        assert_frame_equal(result, self.table)

    def test_contains_case_insensitive(self):
        params = simple_params("a", "text_contains", "fred", case_sensitive=False)
        result = render(self.table, params)
        expected = self.table[[True, True, False, False, True]].reset_index(drop=True)
        assert_frame_equal(result, expected)

    def test_contains_case_sensitive(self):
        params = simple_params("a", "text_contains", "fred", case_sensitive=True)
        result = render(self.table, params)
        expected = self.table[[True, True, False, False, False]].reset_index(drop=True)
        assert_frame_equal(result, expected)

    def test_contains_regex(self):
        params = simple_params(
            "a", "text_contains_regex", "f[a-zA-Z]+d", case_sensitive=True
        )
        result = render(self.table, params)
        expected = self.table[[True, True, False, False, False]].reset_index(drop=True)
        assert_frame_equal(result, expected)

    def test_contains_regex_parse_error(self):
        table = pd.DataFrame({"A": ["a"]})
        params = simple_params("A", "text_contains_regex", "*", case_sensitive=True)
        result = render(table, params)
        self.assertEqual(
            result, "Regex parse error: no argument for repetition operator: *"
        )

    def test_contains_regex_parse_error_case_insensitive(self):
        table = pd.DataFrame({"A": ["a"]})
        params = simple_params("A", "text_contains_regex", "(", case_sensitive=False)
        result = render(table, params)
        self.assertEqual(result, "Regex parse error: missing ): (")

    def test_contains_regex_nan(self):
        table = pd.DataFrame({"A": ["a", np.nan]})
        params = simple_params("A", "text_contains_regex", "a", case_sensitive=True)
        result = render(table, params)
        assert_frame_equal(result, pd.DataFrame({"A": ["a"]}))

    def test_contains_regex_nan_categorical(self):
        table = pd.DataFrame({"A": ["a", np.nan]}, dtype="category")
        params = simple_params("A", "text_contains_regex", "a", case_sensitive=True)
        result = render(table, params)
        assert_frame_equal(result, pd.DataFrame({"A": ["a"]}, dtype="category"))

    def test_contains_regex_case_insensitive(self):
        table = pd.DataFrame({"A": ["a", "A", "b"]})
        params = simple_params("A", "text_contains_regex", "a", case_sensitive=False)
        result = render(table, params)
        assert_frame_equal(result, pd.DataFrame({"A": ["a", "A"]}))

    def test_contains_regex_drop(self):
        params = simple_params(
            "a", "text_contains_regex", "f[a-zA-Z]+d", case_sensitive=True, keep=False
        )
        result = render(self.table, params)
        expected = self.table[[False, False, True, True, True]].reset_index(drop=True)
        assert_frame_equal(result, expected)

    def test_not_contains(self):
        params = simple_params(
            "a", "text_does_not_contain", "fred", case_sensitive=False
        )
        result = render(self.table, params)
        expected = self.table[[False, False, True, True, False]].reset_index(drop=True)
        assert_frame_equal(result, expected)

    def test_not_contains_case_sensitive(self):
        params = simple_params(
            "a", "text_does_not_contain", "fred", case_sensitive=True
        )
        result = render(self.table, params)
        expected = self.table[[False, False, True, True, True]].reset_index(drop=True)
        assert_frame_equal(result, expected)

    def test_not_contains_regex(self):
        table = pd.DataFrame(
            {
                "A": pd.Series([" fredx", "fd", np.nan, "x"], dtype="category"),
                "B": [1, 2, 3, 4],
            }
        )
        params = simple_params(
            "A", "text_does_not_contain_regex", "f[a-zA-Z]+d", case_sensitive=True
        )
        result = render(table, params)
        assert_frame_equal(
            result,
            pd.DataFrame(
                {"A": pd.Series(["fd", np.nan, "x"], dtype="category"), "B": [2, 3, 4]}
            ),
        )

    def test_not_contains_regex_drop(self):
        params = simple_params(
            "a",
            "text_does_not_contain_regex",
            "f[a-zA-Z]+d",
            case_sensitive=True,
            keep=False,
        )
        result = render(self.table, params)
        expected = self.table[[True, True, False, False, False]].reset_index(drop=True)
        assert_frame_equal(result, expected)

    def test_exactly(self):
        params = simple_params("a", "text_is_exactly", "fred", case_sensitive=True)
        result = render(self.table, params)
        expected = self.table[[True, False, False, False, False]].reset_index(drop=True)
        assert_frame_equal(result, expected)

    def test_exactly_empty_str(self):
        params = simple_params("a", "text_is_exactly", "")
        result = render(pd.DataFrame({"a": ["", np.nan, "x"]}), params)
        assert_frame_equal(result, pd.DataFrame({"a": [""]}))

    def test_not_exactly(self):
        params = simple_params("a", "text_is_not_exactly", "x", case_sensitive=True)
        result = render(pd.DataFrame({"a": ["x", "y", "z"]}), params)
        assert_frame_equal(result, pd.DataFrame({"a": ["y", "z"]}))

    def test_not_exactly_empty_str(self):
        params = simple_params("a", "text_is_not_exactly", "")
        result = render(pd.DataFrame({"a": ["", np.nan, "x"]}), params)
        assert_frame_equal(result, pd.DataFrame({"a": [np.nan, "x"]}))

    def test_not_exactly_case_insensitive(self):
        params = simple_params("a", "text_is_not_exactly", "x", case_sensitive=False)
        result = render(pd.DataFrame({"a": ["x", "X", "y"]}), params)
        assert_frame_equal(result, pd.DataFrame({"a": ["y"]}))

    def test_exactly_regex(self):
        table = pd.DataFrame(
            {"A": ["around", "round", "rounded", np.nan, "e"], "B": [1, 2, 3, 4, 5]}
        )
        params = simple_params("A", "text_is_exactly_regex", "round")
        result = render(table, params)
        expected = pd.DataFrame({"A": ["round"], "B": [2]})
        assert_frame_equal(result, expected)

    def test_exactly_non_text_column(self):
        params = simple_params("b", "text_is_exactly", "5")
        result = render(self.table, params)
        self.assertEqual(result, "Column is not text. Please convert to text.")

    def test_null(self):
        params = simple_params("c", "cell_is_empty", "nonsense")
        result = render(self.table, params)
        expected = self.table[[False, True, True, False, True]].reset_index(drop=True)
        assert_frame_equal(result, expected)

        # should not require value
        params = simple_params("c", "cell_is_empty", "")
        result = render(self.table, params)
        assert_frame_equal(result, expected)

    def test_not_null(self):
        params = simple_params("c", "cell_is_not_empty", "nonsense")
        result = render(self.table, params)
        expected = self.table[[True, False, False, True, False]].reset_index(drop=True)
        assert_frame_equal(result, expected)

        # should not require value
        params = simple_params("c", "cell_is_not_empty", "")
        result = render(self.table, params)
        assert_frame_equal(result, expected)

    def test_empty(self):
        params = simple_params("c", "cell_is_empty_str_or_null", "")
        result = render(pd.DataFrame({"c": ["x", "", np.nan, "y"]}), params)
        assert_frame_equal(result, pd.DataFrame({"c": ["", np.nan]}))

    def test_non_empty(self):
        params = simple_params("c", "cell_is_not_empty_str_or_null", "")
        result = render(pd.DataFrame({"c": ["x", "", np.nan, "y"]}), params)
        assert_frame_equal(result, pd.DataFrame({"c": ["x", "y"]}))

    def test_non_empty_with_non_text_input(self):
        # Workbench allows the concept of "empty" on _any_ value -- text or
        # otherwise. With non-text columns, "empty" is a synonym for "null".
        params = simple_params("c", "cell_is_not_empty_str_or_null", "")
        result = render(pd.DataFrame({"c": [0, 1, np.nan, 2]}), params)
        assert_frame_equal(result, pd.DataFrame({"c": [0.0, 1, 2]}))

    def test_equals(self):
        # working as intended
        params = simple_params("c", "number_equals", "3")
        result = render(self.table, params)
        expected = self.table[[True, False, False, False, False]].reset_index(drop=True)
        assert_frame_equal(result, expected)

    def test_equals_non_number_errors(self):
        # non-numeric column should return error message
        params = simple_params("a", "number_equals", "3")
        result = render(self.table, params)
        self.assertEqual(result, "Column is not numbers. Please convert to numbers.")

        # non-numeric column should return error message
        params = simple_params("date", "number_equals", "3")
        result = render(self.table, params)
        self.assertEqual(result, "Column is not numbers. Please convert to numbers.")

        # non-numeric value should return error message
        params = simple_params("c", "number_equals", "gibberish")
        result = render(self.table, params)
        self.assertEqual(result, "Value is not a number. Please enter a valid number.")

    def test_not_equals(self):
        params = simple_params("c", "number_does_not_equal", "3")
        result = render(pd.DataFrame({"c": [1, np.nan, 3, 5]}), params)
        assert_frame_equal(result, pd.DataFrame({"c": [1, np.nan, 5]}))

    def test_category_equals(self):
        table = pd.DataFrame({"A": ["foo", np.nan, "bar"]}, dtype="category")
        params = simple_params("A", "text_is_exactly", "foo", case_sensitive=True)
        result = render(table, params)
        assert_frame_equal(result, pd.DataFrame({"A": ["foo"]}, dtype="category"))

    def test_greater(self):
        # edge case, first row has b=2
        params = simple_params("b", "number_is_greater_than", "2")
        result = render(self.table, params)
        expected = self.table[[False, True, False, True, True]].reset_index(drop=True)
        assert_frame_equal(result, expected)

    def test_greater_equals(self):
        # edge case, first row has b=2
        params = simple_params("b", "number_is_greater_than_or_equals", "2")
        result = render(self.table, params)
        expected = self.table[[True, True, False, True, True]].reset_index(drop=True)
        assert_frame_equal(result, expected)

    def test_less(self):
        # edge case, second and last row has b=5
        params = simple_params("b", "number_is_less_than", "5")
        result = render(self.table, params)
        expected = self.table[[True, False, False, False, False]].reset_index(drop=True)
        assert_frame_equal(result, expected)

    def test_less_equals(self):
        # edge case, second and last row has b=5
        params = simple_params("b", "number_is_less_than_or_equals", "5")
        result = render(self.table, params)
        expected = self.table[[True, True, False, False, True]].reset_index(drop=True)
        assert_frame_equal(result, expected)

    def test_date_is(self):
        params = simple_params("date", "date_is", "2015-07-31")
        result = render(self.table, params)
        expected = self.table[[False, False, False, True, False]].reset_index(drop=True)
        assert_frame_equal(result, expected)

    def test_date_is_not(self):
        params = simple_params("date", "date_is_not", "2015-07-31")
        result = render(
            pd.DataFrame(
                {"date": ["2015-07-31", "2015-07-20"]}, dtype="datetime64[ns]"
            ),
            params,
        )
        expected = pd.DataFrame({"date": ["2015-07-20"]}, dtype="datetime64[ns]")
        assert_frame_equal(result, expected)

    def test_bad_date(self):
        # columns that aren't dates -> error
        params = simple_params("a", "date_is", "2015-7-31")
        result = render(self.table, params)
        self.assertEqual(result, "Column is not dates. Please convert to dates.")

        params = simple_params("b", "date_is", "2015-7-31")
        result = render(self.table, params)
        self.assertEqual(result, "Column is not dates. Please convert to dates.")

        # string that isn't a date -> error
        params = simple_params("date", "date_is", "gibberish")
        result = render(self.table, params)
        self.assertEqual(result, "Value is not a date. Please enter a date and time.")

    def test_date_before(self):
        params = simple_params("date", "date_is_before", "2016-07-31")
        result = render(self.table, params)
        expected = self.table[[False, False, False, True, False]].reset_index(drop=True)
        assert_frame_equal(result, expected)

    def test_date_after(self):
        # edge case, first row is 2018-1-12 08:15 so after implied midnight of
        # date without time
        params = simple_params("date", "date_is_after", "2018-01-12")
        result = render(self.table, params)
        expected = self.table[[False, True, False, False, True]].reset_index(drop=True)
        assert_frame_equal(result, expected)

    def test_datetime_before(self):
        table = pd.DataFrame(
            {"date": ["2019-01-01T04:59+0500", "2019-01-01T05:01+0500"]}
        )
        params = simple_params("date", "date_is_before", "2019-01-01")
        result = render(table, params)
        expected = pd.DataFrame({"date": ["2019-01-01T04:59+0500"]})
        assert_frame_equal(result, expected)

    def test_compare_int_with_str_condition(self):
        params = simple_params("A", "text_is_exactly", " ")
        result = render(pd.DataFrame({"A": []}), params)
        self.assertEqual(result, "Column is not text. Please convert to text.")

    def test_two_filters_and(self):
        table = pd.DataFrame({"A": [1, 2, 3], "B": [2, 3, 4]})
        params = {
            "keep": True,
            "filters": {
                "operator": "and",
                "filters": [
                    {
                        "operator": "or",
                        "subfilters": [
                            {
                                "colname": "A",
                                "condition": "number_is_less_than",
                                "value": "3",
                                "case_sensitive": False,
                            }
                        ],
                    },
                    {
                        "operator": "or",
                        "subfilters": [
                            {
                                "colname": "B",
                                "condition": "number_is_greater_than",
                                "value": "2",
                                "case_sensitive": False,
                            }
                        ],
                    },
                ],
            },
        }
        result = render(table, params)
        assert_frame_equal(result, pd.DataFrame({"A": [2], "B": [3]}))

    def test_two_filters_or(self):
        table = pd.DataFrame({"A": [1, 2, 3], "B": [2, 3, 4]})
        params = {
            "keep": True,
            "filters": {
                "operator": "or",
                "filters": [
                    {
                        "operator": "and",
                        "subfilters": [
                            {
                                "colname": "A",
                                "condition": "number_is_less_than",
                                "value": "2",
                                "case_sensitive": False,
                            }
                        ],
                    },
                    {
                        "operator": "and",
                        "subfilters": [
                            {
                                "colname": "B",
                                "condition": "number_is_greater_than",
                                "value": "3",
                                "case_sensitive": False,
                            }
                        ],
                    },
                ],
            },
        }
        result = render(table, params)
        assert_frame_equal(result, pd.DataFrame({"A": [1, 3], "B": [2, 4]}))

    def test_two_subfilters_and(self):
        table = pd.DataFrame({"A": [1, 2, 3], "B": [2, 3, 4]})
        params = {
            "keep": True,
            "filters": {
                "operator": "or",
                "filters": [
                    {
                        "operator": "and",
                        "subfilters": [
                            {
                                "colname": "A",
                                "condition": "number_is_less_than",
                                "value": "3",
                                "case_sensitive": False,
                            },
                            {
                                "colname": "B",
                                "condition": "number_is_greater_than",
                                "value": "2",
                                "case_sensitive": False,
                            },
                        ],
                    }
                ],
            },
        }
        result = render(table, params)
        assert_frame_equal(result, pd.DataFrame({"A": [2], "B": [3]}))

    def test_two_subfilters_or(self):
        table = pd.DataFrame({"A": [1, 2, 3], "B": [2, 3, 4]})
        params = {
            "keep": True,
            "filters": {
                "operator": "and",
                "filters": [
                    {
                        "operator": "or",
                        "subfilters": [
                            {
                                "colname": "A",
                                "condition": "number_is_less_than",
                                "value": "2",
                                "case_sensitive": False,
                            },
                            {
                                "colname": "B",
                                "condition": "number_is_greater_than",
                                "value": "3",
                                "case_sensitive": False,
                            },
                        ],
                    }
                ],
            },
        }
        result = render(table, params)
        assert_frame_equal(result, pd.DataFrame({"A": [1, 3], "B": [2, 4]}))

    def test_multi_filters_and_subfilters_all_and(self):
        # https://www.pivotaltracker.com/story/show/165434277
        # I couldn't reproduce -- dunno what the issue was. But it's good to
        # test for it!
        table = pd.DataFrame({"A": [1, 2, 3, 4, 5, 6]})
        params = {
            "keep": True,
            "filters": {
                "operator": "and",
                "filters": [
                    {
                        "operator": "and",
                        "subfilters": [
                            {
                                "colname": "A",
                                "condition": "number_is_greater_than",
                                "value": "1",
                                "case_sensitive": False,
                            },
                            {
                                "colname": "A",
                                "condition": "number_is_greater_than",
                                "value": "5",
                                "case_sensitive": False,
                            },
                        ],
                    },
                    {
                        "operator": "and",
                        "subfilters": [
                            {
                                "colname": "A",
                                "condition": "number_is_greater_than",
                                "value": "2",
                                "case_sensitive": False,
                            }
                        ],
                    },
                ],
            },
        }
        result = render(table, params)
        assert_frame_equal(result, pd.DataFrame({"A": [6]}))

    def test_remove_unused_categories(self):
        # [2019-04-23] we're stricter about module output now: categories must
        # all be used, so we don't save too much useless data.
        table = pd.DataFrame({"A": ["a", "b"], "B": ["c", "d"]}, dtype="category")
        params = simple_params("A", "text_contains", "a")
        result = render(table, params)
        assert_frame_equal(
            result, pd.DataFrame({"A": ["a"], "B": ["c"]}, dtype="category")
        )


if __name__ == "__main__":
    unittest.main()
