from typing import List
import unittest
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from extractnumbers import render, Extract, Format, Replace, Form


def F(colnames: List[str]=[], type_extract: Extract=Extract.EXACT,
      type_format: Format=Format.US,
      type_replace: Replace=Replace.NULL):
    """Form(), with default values."""
    return Form(colnames, type_extract, type_format, type_replace)


class TestExtractNumbers(unittest.TestCase):
    def test_NOP(self):
        # should NOP when first applied
        result = F([]).process(pd.DataFrame({'A': ['a', '1']}))
        assert_frame_equal(result, pd.DataFrame({'A': ['a', '1']}))

    def test_ignore_numbers(self):
        table = pd.DataFrame({'A': [1, 2]})
        result = F(['A']).process(table)
        assert_frame_equal(result, pd.DataFrame({'A': [1, 2]}))

    def test_extract_any_from_str(self):
        table = pd.DataFrame({'A': ['1', '2.1', 'note: 3.2', '-3.1']})
        form = F(['A'], Extract.ANY)
        result = form.process(table)
        assert_frame_equal(result, pd.DataFrame({'A': [1.0, 2.1, 3.2, -3.1]}))

    def test_extract_any_from_category(self):
        table = pd.DataFrame({'A': ['1', '2.1', 'note: 3.2']},
                             dtype='category')
        form = F(['A'], Extract.ANY)
        result = form.process(table)
        assert_frame_equal(result, pd.DataFrame({'A': [1.0, 2.1, 3.2]}))

    def test_extract_any_us(self):
        table = pd.DataFrame({'A': ['1,234', '2,345.67', '3.456']})
        form = F(['A'], Extract.ANY, Format.US)
        result = form.process(table)
        assert_frame_equal(result, pd.DataFrame({'A': [1234, 2345.67, 3.456]}))

    def test_extract_any_eu(self):
        table = pd.DataFrame({'A': ['1,234', '2,345.67', '3.456']})
        form = F(['A'], Extract.ANY, Format.EU)
        result = form.process(table)
        assert_frame_equal(result, pd.DataFrame({'A': [1.234, 2.345, 3456]}))

    def test_extract_any_many_commas(self):
        result = F(['A'], Extract.ANY, Format.US).process(pd.DataFrame({
            'A': ['1,234,567,890']
        }))
        assert_frame_equal(result, pd.DataFrame({'A': [1234567890]}))

    def test_extract_any_us_thousands_must_be_in_groups_of_3(self):
        result = F(['A'], Extract.ANY, Format.US).process(pd.DataFrame({
            'A': ['123,4', '2,345,1', '3,23.123']
        }))
        assert_frame_equal(result, pd.DataFrame({'A': [123, 2345, 3]}))

    def test_extract_any_eu_thousands_must_be_in_groups_of_3(self):
        result = F(['A'], Extract.ANY, Format.EU).process(pd.DataFrame({
            'A': ['123.4', '2.345.1', '3.23,123']
        }))
        assert_frame_equal(result, pd.DataFrame({'A': [123, 2345, 3]}))

    def test_extract_exact_eu_thousands_must_be_in_groups_of_3(self):
        result = F(['A'], Extract.EXACT, Format.EU).process(pd.DataFrame({
            'A': ['123.4', '2.345.1', '3.23,123']
        }))
        assert_frame_equal(result,
                           pd.DataFrame({'A': [np.nan, np.nan, np.nan]}))

    def test_extract_integer_from_str(self):
        table = pd.DataFrame({'A': ['1', '2.1', 'note: 3.2', '-3']})
        form = F(['A'], Extract.INTEGER)
        result = form.process(table)
        assert_frame_equal(result, pd.DataFrame({'A': [1, 2, 3, -3]}))

    def test_extract_integer_from_category(self):
        table = pd.DataFrame({'A': ['1', '2.1', 'note: 3.2']},
                             dtype='category')
        form = F(['A'], Extract.INTEGER)
        result = form.process(table)
        assert_frame_equal(result, pd.DataFrame({'A': [1, 2, 3]}))

    def test_extract_integer_no_separator(self):
        table = pd.DataFrame({'A': ['10000', '20001']})
        result = F(['A'], Extract.INTEGER).process(table)
        assert_frame_equal(result, pd.DataFrame({'A': [10000, 20001]}))

    def test_extract_integer_us(self):
        table = pd.DataFrame({'A': ['1,234', '2,345.67', '3.456']})
        form = F(['A'], Extract.INTEGER, Format.US)
        result = form.process(table)
        assert_frame_equal(result, pd.DataFrame({'A': [1234, 2345, 3]}))

    def test_extract_integer_eu(self):
        table = pd.DataFrame({'A': ['1,234', '2,345.67', '3.456']})
        form = F(['A'], Extract.INTEGER, Format.EU)
        result = form.process(table)
        assert_frame_equal(result, pd.DataFrame({'A': [1, 2, 3456]}))

    def test_extract_decimal_from_str(self):
        table = pd.DataFrame({'A': ['1', '2.1', 'note: 3.2']})
        form = F(['A'], Extract.DECIMAL)
        result = form.process(table)
        assert_frame_equal(result, pd.DataFrame({'A': [np.nan, 2.1, 3.2]}))

    def test_extract_decimal_from_category(self):
        table = pd.DataFrame({'A': ['1', '2.1', 'note: 3.2', '-3', '-3.0']},
                             dtype='category')
        form = F(['A'], Extract.DECIMAL)
        result = form.process(table)
        assert_frame_equal(result, pd.DataFrame(
            {'A': [np.nan, 2.1, 3.2, np.nan, -3]}
        ))

    def test_extract_decimal_us(self):
        table = pd.DataFrame({'A': ['1,234', '2,345.67', '3.456']})
        form = F(['A'], Extract.DECIMAL, Format.US)
        result = form.process(table)
        assert_frame_equal(result,
                           pd.DataFrame({'A': [np.nan, 2345.67, 3.456]}))

    def test_extract_decimal_eu(self):
        table = pd.DataFrame({'A': ['1,234', '2,345.67', '3.456']})
        form = F(['A'], Extract.DECIMAL, Format.EU)
        result = form.process(table)
        assert_frame_equal(result, pd.DataFrame({'A': [1.234, 2.345, np.nan]}))

    def test_replace_with_null(self):
        table = pd.DataFrame({'A': ['', '.', np.nan, '1', '2.1']})
        form = F(['A'], Extract.INTEGER, Format.US, Replace.NULL)
        result = form.process(table)
        assert_frame_equal(result,
                           pd.DataFrame({'A': [np.nan, np.nan, np.nan, 1, 2]}))

    def test_replace_with_zero(self):
        table = pd.DataFrame({'A': ['', '.', np.nan, '1', '2.1']})
        form = F(['A'], Extract.INTEGER, Format.US, Replace.ZERO)
        result = form.process(table)
        assert_frame_equal(result,
                           pd.DataFrame({'A': [0, 0, np.nan, 1, 2]}))

    def test_integration(self):
        table = pd.DataFrame(
            {'A': ['1', '2'], 'B': ['2', '3'], 'C': ['3', '4']}
        )
        result = render(table, {
            'colnames': 'A,B',
            'extract': False,
            'type_extract': 1,
            'type_format': 0,
            'type_replace': 0,
        })
        assert_frame_equal(result, pd.DataFrame(
            {'A': [1, 2], 'B': [2, 3], 'C': ['3', '4']}
        ))
