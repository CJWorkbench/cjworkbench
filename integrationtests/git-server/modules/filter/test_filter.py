import unittest
from typing import Any, Dict
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from filter import render, migrate_params


def simple_params(colname: str, condition: str, value: str,
                  case_sensitive: bool=False,
                  keep: bool=True) -> Dict[str, Any]:
    return {
        'keep': 0 if keep else 1,
        'filters': {
            'operator': 'and',
            'filters': [
                {
                    'operator': 'and',
                    'subfilters': [
                        {
                            'colname': colname,
                            'condition': condition,
                            'value': value,
                            'case_sensitive': case_sensitive,
                        },
                    ],
                },
            ],
        },
    }


class TestMigrateParams(unittest.TestCase):
    def test_v0_select_stays_select(self):
        self.assertEqual(
            migrate_params({
                'column': 'A',
                'condition': 0,  # "Select" (the default)
                'value': 'value',
                'casesensitive': False,
                'keep': 0,  # "Keep"
                'regex': False,
            }),
            simple_params('A', '', 'value')
        )

    def test_v0_text_contains_without_regex_stays_text_contains(self):
        self.assertEqual(
            migrate_params({
                'column': 'A',
                'condition': 2,  # "Text contains"
                'value': 'value',
                'casesensitive': False,
                'keep': 0,  # "Keep"
                'regex': False,
            }),
            simple_params('A', 'text_contains', 'value')
        )

    def test_v0_text_contains_regex_changes_condition(self):
        self.assertEqual(
            migrate_params({
                'column': 'A',
                'condition': 2,  # "Text contains"
                'value': 'value',
                'casesensitive': False,
                'keep': 0,  # "Keep"
                'regex': True,
            }),
            simple_params('A', 'text_contains_regex', 'value')
        )

    def test_v0_cell_is_empty_changes_number(self):
        self.assertEqual(
            migrate_params({
                'column': 'A',
                'condition': 6,  # "Cell is empty"
                'value': 'value',
                'casesensitive': False,
                'keep': 0,  # "Keep"
                'regex': True,
            }),
            simple_params('A', 'cell_is_empty', 'value')
        )

    def test_v0_from_dropdown(self):
        self.assertEqual(
            migrate_params({
                'column': 'A',
            }),
            simple_params('A', '', '')
        )


class TestRender(unittest.TestCase):
    def setUp(self):
        # Test data includes some partially and completely empty rows because
        # this tends to freak out Pandas
        self.table = pd.DataFrame(
            [['fred', 2, 3, 'round', '2018-1-12'],
             ['frederson', 5, np.nan, 'square', '2018-1-12 08:15'],
             [np.nan, np.nan, np.nan, np.nan, np.nan],
             ['maggie', 8, 10, 'Round', '2015-7-31'],
             ['Fredrick', 5, np.nan, 'square', '2018-3-12']],
            columns=['a', 'b', 'c', 'd', 'date'])

    def test_no_column(self):
        params = simple_params('', 'text_contains', 'fred')
        result = render(self.table, params)
        assert_frame_equal(result, self.table)

    def test_no_value(self):
        params = simple_params('a', 'text_contains', '')
        result = render(self.table, params)
        assert_frame_equal(result, self.table)

    def test_illegal_condition(self):
        params = simple_params('a', '', 'value')
        result = render(self.table, params)
        assert_frame_equal(result, self.table)

    def test_contains_case_insensitive(self):
        params = simple_params('a', 'text_contains', 'fred',
                               case_sensitive=False)
        result = render(self.table, params)
        expected = self.table[[True, True, False, False,
                               True]].reset_index(drop=True)
        assert_frame_equal(result, expected)

    def test_contains_case_sensitive(self):
        params = simple_params('a', 'text_contains', 'fred',
                               case_sensitive=True)
        result = render(self.table, params)
        expected = self.table[[True, True, False, False,
                               False]].reset_index(drop=True)
        assert_frame_equal(result, expected)

    def test_contains_regex(self):
        params = simple_params('a', 'text_contains_regex', 'f[a-zA-Z]+d',
                               case_sensitive=True)
        result = render(self.table, params)
        expected = self.table[[True, True, False, False,
                               False]].reset_index(drop=True)
        assert_frame_equal(result, expected)

    def test_contains_regex_drop(self):
        params = simple_params('a', 'text_contains_regex', 'f[a-zA-Z]+d',
                               case_sensitive=True, keep=False)
        result = render(self.table, params)
        expected = self.table[[False, False, True, True,
                               True]].reset_index(drop=True)
        assert_frame_equal(result, expected)

    def test_not_contains(self):
        params = simple_params('a', 'text_does_not_contain', 'fred',
                               case_sensitive=False)
        result = render(self.table, params)
        expected = self.table[[False, False, True, True,
                               False]].reset_index(drop=True)
        assert_frame_equal(result, expected)

    def test_not_contains_case_sensitive(self):
        params = simple_params('a', 'text_does_not_contain', 'fred',
                               case_sensitive=True)
        result = render(self.table, params)
        expected = self.table[[False, False, True, True,
                               True]].reset_index(drop=True)
        assert_frame_equal(result, expected)

    def test_not_contains_regex(self):
        params = simple_params('a', 'text_does_not_contain_regex',
                               'f[a-zA-Z]+d', case_sensitive=True)
        result = render(self.table, params)
        expected = self.table[[False, False, True, True,
                               True]].reset_index(drop=True)
        assert_frame_equal(result, expected)

    def test_not_contains_regex_drop(self):
        params = simple_params('a', 'text_does_not_contain_regex',
                               'f[a-zA-Z]+d', case_sensitive=True,
                               keep=False)
        result = render(self.table, params)
        expected = self.table[[True, True, False, False,
                               False]].reset_index(drop=True)
        assert_frame_equal(result, expected)

    def test_exactly(self):
        params = simple_params('a', 'text_is_exactly', 'fred',
                               case_sensitive=True)
        result = render(self.table, params)
        expected = self.table[[True, False, False, False,
                               False]].reset_index(drop=True)
        assert_frame_equal(result, expected)

    def test_exactly_regex(self):
        params = simple_params('d', 'text_is_exactly_regex', 'round')
        result = render(self.table, params)
        expected = self.table[[True, False, False, True,
                               False]].reset_index(drop=True)
        assert_frame_equal(result, expected)

    def test_exactly_non_text_column(self):
        params = simple_params('b', 'text_is_exactly', '5')
        result = render(self.table, params)
        self.assertEqual(result, 'Column is not text. Please convert to text.')

    def test_empty(self):
        params = simple_params('c', 'cell_is_empty', 'nonsense')
        result = render(self.table, params)
        expected = self.table[[False, True, True, False,
                               True]].reset_index(drop=True)
        assert_frame_equal(result, expected)

        # should not require value
        params = simple_params('c', 'cell_is_empty', '')
        result = render(self.table, params)
        assert_frame_equal(result, expected)

    def test_not_empty(self):
        params = simple_params('c', 'cell_is_not_empty', 'nonsense')
        result = render(self.table, params)
        expected = self.table[[True, False, False, True,
                               False]].reset_index(drop=True)
        assert_frame_equal(result, expected)

        # should not require value
        params = simple_params('c', 'cell_is_not_empty', '')
        result = render(self.table, params)
        assert_frame_equal(result, expected)

    def test_equals(self):
        # working as intended
        params = simple_params('c', 'number_equals', '3')
        result = render(self.table, params)
        expected = self.table[[True, False, False, False,
                               False]].reset_index(drop=True)
        assert_frame_equal(result, expected)

    def test_equals_non_number_errors(self):
        # non-numeric column should return error message
        params = simple_params('a', 'number_equals', '3')
        result = render(self.table, params)
        self.assertEqual(result,
                         'Column is not numbers. Please convert to numbers.')

        # non-numeric column should return error message
        params = simple_params('date', 'number_equals', '3')
        result = render(self.table, params)
        self.assertEqual(result,
                         'Column is not numbers. Please convert to numbers.')

        # non-numeric value should return error message
        params = simple_params('c', 'number_equals', 'gibberish')
        result = render(self.table, params)
        self.assertEqual(result,
                         'Value is not a number. Please enter a valid number.')

    def test_category_equals(self):
        table = pd.DataFrame({'A': ['foo', np.nan, 'bar']}, dtype='category')
        params = simple_params('A', 'text_is_exactly', 'foo',
                               case_sensitive=True)
        result = render(table, params)

        # Output is categorical with [foo, bar] categories. We _could_ remove
        # the unused category, but there's no value added there.
        assert_frame_equal(
            result,
            pd.DataFrame({'A': ['foo']}, dtype=table['A'].dtype)
        )

    def test_greater(self):
        # edge case, first row has b=2
        params = simple_params('b', 'number_is_greater_than', '2')
        result = render(self.table, params)
        expected = self.table[[False, True, False, True,
                               True]].reset_index(drop=True)
        assert_frame_equal(result, expected)

    def test_greater_equals(self):
        # edge case, first row has b=2
        params = simple_params('b', 'number_is_greater_than_or_equals', '2')
        result = render(self.table, params)
        expected = self.table[[True, True, False, True,
                               True]].reset_index(drop=True)
        assert_frame_equal(result, expected)

    def test_less(self):
        # edge case, second and last row has b=5
        params = simple_params('b', 'number_is_less_than', '5')
        result = render(self.table, params)
        expected = self.table[[True, False, False, False,
                               False]].reset_index(drop=True)
        assert_frame_equal(result, expected)

    def test_less_equals(self):
        # edge case, second and last row has b=5
        params = simple_params('b', 'number_is_less_than_or_equals', '5')
        result = render(self.table, params)
        expected = self.table[[True, True, False, False,
                               True]].reset_index(drop=True)
        assert_frame_equal(result, expected)

    def test_date_is(self):
        params = simple_params('date', 'date_is', '2015-07-31')
        result = render(self.table, params)
        expected = self.table[[False, False, False, True,
                               False]].reset_index(drop=True)
        assert_frame_equal(result, expected)

    def test_bad_date(self):
        # columns that aren't dates -> error
        params = simple_params('a', 'date_is', '2015-7-31')
        result = render(self.table, params)
        self.assertEqual(result,
                         'Column is not dates. Please convert to dates.')

        params = simple_params('b', 'date_is', '2015-7-31')
        result = render(self.table, params)
        self.assertEqual(result,
                         'Column is not dates. Please convert to dates.')

        # string that isn't a date -> error
        params = simple_params('date', 'date_is', 'gibberish')
        result = render(self.table, params)
        self.assertEqual(result,
                         'Value is not a date. Please enter a date and time.')

    def test_date_before(self):
        params = simple_params('date', 'date_is_before', '2016-07-31')
        result = render(self.table, params)
        expected = self.table[[False, False, False, True,
                               False]].reset_index(drop=True)
        assert_frame_equal(result, expected)

    def test_date_after(self):
        # edge case, first row is 2018-1-12 08:15 so after implied midnight of
        # date without time
        params = simple_params('date', 'date_is_after', '2018-01-12')
        result = render(self.table, params)
        expected = self.table[[False, True, False, False,
                               True]].reset_index(drop=True)
        assert_frame_equal(result, expected)

    def test_compare_int_with_str_condition(self):
        params = simple_params('A', 'text_is_exactly', ' ')
        result = render(pd.DataFrame({'A': []}), params)
        self.assertEqual(result, 'Column is not text. Please convert to text.')

    def test_two_filters_and(self):
        table = pd.DataFrame({'A': [1, 2, 3], 'B': [2, 3, 4]})
        params = {
            'keep': 0,
            'filters': {
                'operator': 'and',
                'filters': [
                    {
                        'operator': 'or',
                        'subfilters': [
                            {
                                'colname': 'A',
                                'condition': 'number_is_less_than',
                                'value': 3,
                                'case_sensitive': False,
                            },
                        ],
                    },
                    {
                        'operator': 'or',
                        'subfilters': [
                            {
                                'colname': 'B',
                                'condition': 'number_is_greater_than',
                                'value': 2,
                                'case_sensitive': False,
                            },
                        ],
                    },
                ],
            },
        }
        result = render(table, params)
        assert_frame_equal(result, pd.DataFrame({'A': [2], 'B': [3]}))

    def test_two_filters_or(self):
        table = pd.DataFrame({'A': [1, 2, 3], 'B': [2, 3, 4]})
        params = {
            'keep': 0,
            'filters': {
                'operator': 'or',
                'filters': [
                    {
                        'operator': 'and',
                        'subfilters': [
                            {
                                'colname': 'A',
                                'condition': 'number_is_less_than',
                                'value': 2,
                                'case_sensitive': False,
                            },
                        ],
                    },
                    {
                        'operator': 'and',
                        'subfilters': [
                            {
                                'colname': 'B',
                                'condition': 'number_is_greater_than',
                                'value': 3,
                                'case_sensitive': False,
                            },
                        ],
                    },
                ],
            },
        }
        result = render(table, params)
        assert_frame_equal(result, pd.DataFrame({'A': [1, 3], 'B': [2, 4]}))

    def test_two_subfilters_and(self):
        table = pd.DataFrame({'A': [1, 2, 3], 'B': [2, 3, 4]})
        params = {
            'keep': 0,
            'filters': {
                'operator': 'or',
                'filters': [
                    {
                        'operator': 'and',
                        'subfilters': [
                            {
                                'colname': 'A',
                                'condition': 'number_is_less_than',
                                'value': 3,
                                'case_sensitive': False,
                            },
                            {
                                'colname': 'B',
                                'condition': 'number_is_greater_than',
                                'value': 2,
                                'case_sensitive': False,
                            },
                        ],
                    },
                ],
            },
        }
        result = render(table, params)
        assert_frame_equal(result, pd.DataFrame({'A': [2], 'B': [3]}))

    def test_two_subfilters_or(self):
        table = pd.DataFrame({'A': [1, 2, 3], 'B': [2, 3, 4]})
        params = {
            'keep': 0,
            'filters': {
                'operator': 'and',
                'filters': [
                    {
                        'operator': 'or',
                        'subfilters': [
                            {
                                'colname': 'A',
                                'condition': 'number_is_less_than',
                                'value': 2,
                                'case_sensitive': False,
                            },
                            {
                                'colname': 'B',
                                'condition': 'number_is_greater_than',
                                'value': 3,
                                'case_sensitive': False,
                            },
                        ],
                    },
                ],
            },
        }
        result = render(table, params)
        assert_frame_equal(result, pd.DataFrame({'A': [1, 3], 'B': [2, 4]}))


if __name__ == '__main__':
    unittest.main()
