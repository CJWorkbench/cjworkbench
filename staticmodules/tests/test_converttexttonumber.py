import unittest
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from staticmodules.converttexttonumber import (
    render,
    InputNumberType,
    InputLocale,
    Form,
    migrate_params,
)


class TestMigrateParams(unittest.TestCase):
    def test_v0(self):
        self.assertEqual(
            migrate_params(
                {
                    "extract": True,
                    "colnames": "A,B,C",
                    "type_format": 0,
                    "type_extract": 0,
                    "type_replace": 1,
                }
            ),
            {
                "extract": True,
                "colnames": ["A", "B", "C"],
                "input_number_type": "any",
                "input_locale": "us",
                "error_means_null": True,
                "output_format": "{:,}",
            },
        )

    def test_v1_no_colnames(self):
        self.assertEqual(
            migrate_params(
                {
                    "extract": False,
                    "colnames": "",
                    "input_number_type": "float",
                    "input_locale": "us",
                    "error_means_null": False,
                    "output_format": "{:,}",
                }
            ),
            {
                "extract": False,
                "colnames": [],
                "input_number_type": "float",
                "input_locale": "us",
                "error_means_null": False,
                "output_format": "{:,}",
            },
        )

    def test_v1_with_colnames(self):
        self.assertEqual(
            migrate_params(
                {
                    "extract": False,
                    "colnames": "A,B,C",
                    "input_number_type": "float",
                    "input_locale": "us",
                    "error_means_null": False,
                    "output_format": "{:,}",
                }
            ),
            {
                "extract": False,
                "colnames": ["A", "B", "C"],
                "input_number_type": "float",
                "input_locale": "us",
                "error_means_null": False,
                "output_format": "{:,}",
            },
        )

    def test_v2(self):
        self.assertEqual(
            migrate_params(
                {
                    "extract": False,
                    "colnames": ["A", "B", "C"],
                    "input_number_type": "float",
                    "input_locale": "us",
                    "error_means_null": False,
                    "output_format": "{:,}",
                }
            ),
            {
                "extract": False,
                "colnames": ["A", "B", "C"],
                "input_number_type": "float",
                "input_locale": "us",
                "error_means_null": False,
                "output_format": "{:,}",
            },
        )


class TestExtractNumbers(unittest.TestCase):
    def test_ignore_numbers(self):
        table = pd.DataFrame({"A": [1, 2]})
        result = Form(["A"]).convert_table(table)
        assert_frame_equal(result, pd.DataFrame({"A": [1, 2]}))

    def test_match_unicode_minus(self):
        table = pd.DataFrame({"A": ["-1", "\u22122"]})
        result = Form(["A"]).convert_table(table)
        assert_frame_equal(result, pd.DataFrame({"A": [-1, -2]}))

    def test_extract_any_from_str(self):
        table = pd.DataFrame({"A": ["1", "2.1", "note: 3.2", "-3.1"]})
        form = Form(["A"], True, InputNumberType.ANY, error_means_null=True)
        result = form.convert_table(table)
        assert_frame_equal(result, pd.DataFrame({"A": [1.0, 2.1, 3.2, -3.1]}))

    def test_extract_any_from_category(self):
        table = pd.DataFrame({"A": ["1", "2.1", "note: 3.2"]}, dtype="category")
        form = Form(["A"], True, InputNumberType.ANY)
        result = form.convert_table(table)
        assert_frame_equal(result, pd.DataFrame({"A": [1.0, 2.1, 3.2]}))

    def test_extract_any_us(self):
        table = pd.DataFrame({"A": ["1,234", "2,345.67", "3.456"]})
        form = Form(["A"], True, InputNumberType.ANY, InputLocale.US)
        result = form.convert_table(table)
        assert_frame_equal(result, pd.DataFrame({"A": [1234, 2345.67, 3.456]}))

    def test_extract_any_eu(self):
        table = pd.DataFrame({"A": ["1,234", "2,345.67", "3.456"]})
        form = Form(["A"], True, InputNumberType.ANY, InputLocale.EU)
        result = form.convert_table(table)
        assert_frame_equal(result, pd.DataFrame({"A": [1.234, 2.345, 3456]}))

    def test_extract_any_many_commas(self):
        result = Form(["A"], True, InputNumberType.ANY, InputLocale.US).convert_table(
            pd.DataFrame({"A": ["1,234,567,890"]})
        )
        assert_frame_equal(result, pd.DataFrame({"A": [1234567890]}))

    def test_extract_any_us_thousands_must_be_in_groups_of_3(self):
        form = Form(["A"], True, InputNumberType.ANY, InputLocale.US, True)
        result = form.convert_table(
            pd.DataFrame({"A": ["123,4", "2,345,1", "3,23.123"]})
        )
        assert_frame_equal(result, pd.DataFrame({"A": [123, 2345, 3]}))

    def test_extract_any_eu_thousands_must_be_in_groups_of_3(self):
        form = Form(["A"], True, InputNumberType.ANY, InputLocale.EU, True)
        result = form.convert_table(
            pd.DataFrame({"A": ["123.4", "2.345.1", "3.23,123"]})
        )
        assert_frame_equal(result, pd.DataFrame({"A": [123, 2345, 3]}))

    def test_match_eu_thousands_must_be_in_groups_of_3(self):
        form = Form(
            ["A"], False, InputNumberType.ANY, InputLocale.EU, error_means_null=True
        )
        result = form.convert_table(
            pd.DataFrame({"A": ["123.4", "2.345.1", "3.23,123"]})
        )
        assert_frame_equal(result, pd.DataFrame({"A": [np.nan, np.nan, np.nan]}))

    def test_extract_integer_from_str(self):
        table = pd.DataFrame({"A": ["1", "2.1", "note: 3.2", "-3"]})
        form = Form(["A"], True, InputNumberType.INTEGER)
        result = form.convert_table(table)
        assert_frame_equal(result, pd.DataFrame({"A": [1, 2, 3, -3]}))

    def test_extract_integer_from_category(self):
        table = pd.DataFrame({"A": ["1", "2.1", "note: 3.2"]}, dtype="category")
        form = Form(["A"], True, InputNumberType.INTEGER)
        result = form.convert_table(table)
        assert_frame_equal(result, pd.DataFrame({"A": [1, 2, 3]}))

    def test_extract_integer_no_separator(self):
        table = pd.DataFrame({"A": ["10000", "20001"]})
        result = Form(["A"], True, InputNumberType.INTEGER).convert_table(table)
        assert_frame_equal(result, pd.DataFrame({"A": [10000, 20001]}))

    def test_extract_integer_us(self):
        table = pd.DataFrame({"A": ["1,234", "2,345.67", "3.456"]})
        form = Form(["A"], True, InputNumberType.INTEGER, InputLocale.US)
        result = form.convert_table(table)
        assert_frame_equal(result, pd.DataFrame({"A": [1234, 2345, 3]}))

    def test_extract_integer_eu(self):
        table = pd.DataFrame({"A": ["1,234", "2,345.67", "3.456"]})
        form = Form(["A"], True, InputNumberType.INTEGER, InputLocale.EU)
        result = form.convert_table(table)
        assert_frame_equal(result, pd.DataFrame({"A": [1, 2, 3456]}))

    def test_extract_float_from_str(self):
        table = pd.DataFrame({"A": ["1", "2.1", "note: 3.2"]})
        form = Form(["A"], True, InputNumberType.FLOAT, error_means_null=True)
        result = form.convert_table(table)
        assert_frame_equal(result, pd.DataFrame({"A": [np.nan, 2.1, 3.2]}))

    def test_extract_float_from_category(self):
        table = pd.DataFrame(
            {"A": ["1", "2.1", "note: 3.2", "-3", "-3.0"]}, dtype="category"
        )
        form = Form(["A"], True, InputNumberType.FLOAT, error_means_null=True)
        result = form.convert_table(table)
        assert_frame_equal(result, pd.DataFrame({"A": [np.nan, 2.1, 3.2, np.nan, -3]}))

    def test_extract_float_us(self):
        table = pd.DataFrame({"A": ["1,234", "2,345.67", "3.456"]})
        form = Form(
            ["A"], True, InputNumberType.FLOAT, InputLocale.US, error_means_null=True
        )
        result = form.convert_table(table)
        assert_frame_equal(result, pd.DataFrame({"A": [np.nan, 2345.67, 3.456]}))

    def test_extract_float_eu(self):
        table = pd.DataFrame({"A": ["1,234", "2,345.67", "3.456"]})
        form = Form(
            ["A"], True, InputNumberType.FLOAT, InputLocale.EU, error_means_null=True
        )
        result = form.convert_table(table)
        assert_frame_equal(result, pd.DataFrame({"A": [1.234, 2.345, np.nan]}))

    def test_replace_with_null(self):
        table = pd.DataFrame({"A": ["", ".", np.nan, "1", "2.1"]})
        form = Form(["A"], True, InputNumberType.INTEGER, InputLocale.US, True)
        result = form.convert_table(table)
        assert_frame_equal(result, pd.DataFrame({"A": [np.nan, np.nan, np.nan, 1, 2]}))

    def test_error_on_no_match(self):
        table = pd.DataFrame({"A": ["", ".", np.nan, "1", "2.1"]})
        form = Form(["A"], True, InputNumberType.INTEGER, InputLocale.US)
        result = form.convert_table(table)
        self.assertEqual(
            result,
            (
                "'' in row 1 of 'A' cannot be converted. Overall, there are 2 "
                "errors in 1 column. Select 'Convert non-numbers to null' to set "
                "these values to null."
            ),
        )

    def test_integration_no_op_when_no_columns(self):
        table = pd.DataFrame({"A": ["1", "2"], "B": ["2", "3"], "C": ["3", "4"]})
        result = render(
            table,
            {
                "colnames": [],
                "extract": True,
                "input_number_type": "integer",
                "input_locale": "us",
                "error_means_null": False,
                "output_format": "{:,d}",
            },
        )
        assert_frame_equal(
            result, pd.DataFrame({"A": ["1", "2"], "B": ["2", "3"], "C": ["3", "4"]})
        )

    def test_integration(self):
        table = pd.DataFrame({"A": ["1", "2"], "B": ["2", "3"], "C": ["3", "4"]})
        result = render(
            table,
            {
                "colnames": ["A", "B"],
                "extract": False,
                "input_number_type": "any",
                "input_locale": "us",
                "error_means_null": False,
                "output_format": "{:,d}",
            },
        )
        assert_frame_equal(
            result["dataframe"],
            pd.DataFrame({"A": [1, 2], "B": [2, 3], "C": ["3", "4"]}),
        )
        self.assertEqual(result["column_formats"], {"A": "{:,d}", "B": "{:,d}"})
