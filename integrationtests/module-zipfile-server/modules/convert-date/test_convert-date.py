import importlib
import unittest

import numpy as np
import pandas as pd
from cjwmodule.testing.i18n import i18n_message
from pandas.testing import assert_frame_equal

render = importlib.import_module("convert-date").render
migrate_params = importlib.import_module("convert-date").migrate_params


class MigrateParamsTests(unittest.TestCase):
    def test_v0(self):
        result = migrate_params(
            {"colnames": "report_date", "type_date": 1, "type_null": True}
        )
        self.assertEqual(
            result,
            {
                "colnames": ["report_date"],
                "input_format": "us",
                "error_means_null": True,
            },
        )

    def test_v1_no_colnames(self):
        result = migrate_params(
            {"colnames": "", "input_format": "us", "error_means_null": True}
        )
        self.assertEqual(
            result, {"colnames": [], "input_format": "us", "error_means_null": True}
        )

    def test_v1(self):
        result = migrate_params(
            {
                "colnames": "report_date,A",
                "input_format": "us",
                "error_means_null": True,
            }
        )
        self.assertEqual(
            result,
            {
                "colnames": ["report_date", "A"],
                "input_format": "us",
                "error_means_null": True,
            },
        )

    def test_v2(self):
        result = migrate_params(
            {
                "colnames": ["report_date"],
                "input_format": "us",
                "error_means_null": True,
            }
        )
        self.assertEqual(
            result,
            {
                "colnames": ["report_date"],
                "input_format": "us",
                "error_means_null": True,
            },
        )


def P(colnames=[], input_format="auto", error_means_null=True):
    """Factory method to build params dict."""
    return {
        "colnames": colnames,
        "input_format": input_format,
        "error_means_null": error_means_null,
    }


class ConverttodateTests(unittest.TestCase):
    def test_no_column_no_op(self):
        # should NOP when first applied
        table = pd.DataFrame({"A": [1, 2]})
        params = {"colnames": []}
        result = render(table, params)
        assert_frame_equal(result, table)

    def test_us(self):
        # All values should have the same date
        reference_date = np.datetime64("2018-08-07T00:00:00")
        table = pd.DataFrame(
            {"A": ["08/07/2018", " 08/07/2018T00:00:00 ", "..08/07/2018T00:00:00:00.."]}
        )
        expected = pd.DataFrame({"A": [reference_date] * 3})
        result = render(table, P(["A"], "us"))
        assert_frame_equal(result, expected)

    def test_eu(self):
        # All values should have the same date
        reference_date = np.datetime64("2018-08-07T00:00:00")
        table = pd.DataFrame(
            {"A": ["07/08/2018", " 07/08/2018T00:00:00 ", "..07/08/2018T00:00:00.."]}
        )
        expected = pd.DataFrame({"A": [reference_date] * 3})
        result = render(table, P(["A"], "eu"))
        assert_frame_equal(result, expected)

    def test_categories_behave_like_values(self):
        # https://www.pivotaltracker.com/story/show/167858839
        # Work around https://github.com/pandas-dev/pandas/issues/27952
        table = pd.DataFrame({"A": ["2019-01-01", "2019-02-01"] * 26}, dtype="category")
        expected = pd.DataFrame(
            {"A": ["2019-01-01", "2019-02-01"] * 26}, dtype="datetime64[ns]"
        )
        result = render(table, P(["A"], "auto"))
        assert_frame_equal(result, expected)

    def test_categories_do_not_destroy_cache(self):
        # https://www.pivotaltracker.com/story/show/167858839
        table = pd.DataFrame(
            {"A": ["2019-01-01", "2019-01-01T00:00:00.000"] * 26}, dtype="category"
        )
        expected = pd.DataFrame({"A": ["2019-01-01"] * 52}, dtype="datetime64[ns]")
        result = render(table, P(["A"], "auto"))
        assert_frame_equal(result, expected)

    def test_numbers(self):
        # For now, assume value is year and cast to string
        table = pd.DataFrame({"number": [2018, 1960, 99999]})
        expected = pd.DataFrame(
            {
                "number": [
                    np.datetime64("2018-01-01T00:00:00.000000000"),
                    np.datetime64("1960-01-01T00:00:00.000000000"),
                    pd.NaT,
                ]
            }
        )

        result = render(table.copy(), P(["number"], "auto", True))
        assert_frame_equal(result, expected)

    def test_iso8601_tz_aware_plus_non_tz_aware(self):
        table = pd.DataFrame(
            {"A": ["2019-01-01T00:00:00.000", "2019-03-02T12:02:13.000Z"]},
            dtype="category",
        )
        result = render(table, P(["A"], "auto"))
        assert_frame_equal(
            result,
            pd.DataFrame(
                {
                    "A": [
                        np.datetime64("2019-01-01T00:00:00.000"),
                        np.datetime64("2019-03-02T12:02:13.000"),
                    ]
                }
            ),
        )

    def test_auto(self):
        reference_date = np.datetime64("2018-08-07T00:00:00")
        table = pd.DataFrame(
            {
                "written": ["August 7, 2018", "August 07, 2018", "August 07, 2018"],
                "yearfirst": [
                    "2018-08-07",
                    " 2018.08.07T00:00:00 ",
                    "..2018.08.07T00:00:00..",
                ],
            }
        )
        expected = pd.DataFrame(
            {"written": [reference_date] * 3, "yearfirst": [reference_date] * 3}
        )
        result = render(table.copy(), P(["written", "yearfirst"], "auto", True))
        assert_frame_equal(result, expected)

    def test_date_input(self):
        reference_date = np.datetime64("2018-08-07T00:00:00")
        table = pd.DataFrame({"A": [reference_date, pd.NaT, reference_date]})
        expected = table.copy()
        result = render(table.copy(), P(["A"], "auto", False))
        assert_frame_equal(result, expected)

    def test_multi_types_error(self):
        reference_date = np.datetime64("2018-08-07T00:00:00")
        table = pd.DataFrame(
            {
                "A": [reference_date, pd.NaT, reference_date],
                "B": ["not a date", "another bad date", "no way"],
            }
        )
        result = render(table.copy(), P(["A", "B"], "auto", False))
        self.assertEqual(
            result,
            i18n_message(
                "ErrorCount.message",
                {
                    "a_value": "not a date",
                    "a_row": 1,
                    "a_column": "B",
                    "n_errors": 3,
                    "n_columns": 1,
                }
            ),
        )

    def test_categories(self):
        reference_date = np.datetime64("2018-08-07T00:00:00")
        table = pd.DataFrame({"A": ["August 7, 2018", None, "T8"]}, dtype="category")
        expected = pd.DataFrame({"A": [reference_date, pd.NaT, pd.NaT]})
        result = render(table.copy(), P(["A"], "auto", True))
        assert_frame_equal(result, expected)

    def test_null_input_is_not_error(self):
        table = pd.DataFrame({"null": ["08/07/2018", None, 99]})
        result = render(table, P(["null"], "auto", False))
        self.assertEqual(
            result,
            i18n_message(
                "ErrorCount.message",
                {
                    "a_value": "99",
                    "a_row": 3,
                    "a_column": "null",
                    "n_errors": 1,
                    "n_columns": 1,
                }
            ),
        )

    def test_error(self):
        table = pd.DataFrame({"null": ["08/07/2018", "99", "98"]})
        result = render(table, P(["null"], "auto", False))
        self.assertEqual(
            result,
            i18n_message(
                "ErrorCount.message",
                {
                    "a_value": "99",
                    "a_row": 2,
                    "a_column": "null",
                    "n_errors": 2,
                    "n_columns": 1,
                }
            ),
        )

    def test_error_multicolumn(self):
        table = pd.DataFrame(
            {"null": ["08/07/2018", "99", "99"], "number": [1960, 2018, 99999]}
        )
        result = render(table, P(["null", "number"], "auto", False))
        self.assertEqual(
            result,
            i18n_message(
                "ErrorCount.message",
                {
                    "a_value": "99",
                    "a_row": 2,
                    "a_column": "null",
                    "n_errors": 3,
                    "n_columns": 2,
                }
            ),
        )

    def test_error_multicolumn_first_on_row_0(self):
        # Regression, 2019-08-19: `error_count.a_row` was 0, so `rhs.a_row` was
        # chosen instead, but it was None.
        table = pd.DataFrame({"A": ["bad"], "B": [None]}, dtype=str)
        result = render(table, P(["A", "B"], "auto", False))
        self.assertEqual(
            result,
            i18n_message(
                "ErrorCount.message",
                {
                    "a_value": "bad",
                    "a_row": 1,
                    "a_column": "A",
                    "n_errors": 1,
                    "n_columns": 1,
                },
            ),
        )


if __name__ == "__main__":
    unittest.main()
