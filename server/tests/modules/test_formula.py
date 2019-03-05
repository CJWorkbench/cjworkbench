import unittest
from typing import Any, Dict
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from cjworkbench.types import ProcessResult
from server.modules import formula
from .util import MockParams


P = MockParams.factory(syntax='excel', out_column='R', formula_excel='',
                       all_rows=False, formula_python='')


class MigrateParamsTests(unittest.TestCase):
    def test_v0_excel(self):
        result = formula.migrate_params({
            'syntax': 0,
            'out_column': 'R',
            'formula_excel': '=A1',
            'formula_python': 'A',
            'all_rows': True,
        })
        self.assertEqual(result, {
            'syntax': 'excel',
            'out_column': 'R',
            'formula_excel': '=A1',
            'formula_python': 'A',
            'all_rows': True,
        })

    def test_v0_python(self):
        result = formula.migrate_params({
            'syntax': 1,
            'out_column': 'R',
            'formula_excel': '=A1',
            'formula_python': 'A',
            'all_rows': True,
        })
        self.assertEqual(result, {
            'syntax': 'python',
            'out_column': 'R',
            'formula_excel': '=A1',
            'formula_python': 'A',
            'all_rows': True,
        })

    def test_v1(self):
        result = formula.migrate_params({
            'syntax': 'python',
            'out_column': 'R',
            'formula_excel': '=A1',
            'formula_python': 'A',
            'all_rows': True,
        })
        self.assertEqual(result, {
            'syntax': 'python',
            'out_column': 'R',
            'formula_excel': '=A1',
            'formula_python': 'A',
            'all_rows': True,
        })


class FormulaTests(unittest.TestCase):
    def _test(self, table: pd.DataFrame, params: Dict[str, Any]={},
              expected_table: pd.DataFrame=pd.DataFrame(),
              expected_error: str=''):
        result = ProcessResult.coerce(formula.render(table, P(**params)))
        result.sanitize_in_place()

        expected = ProcessResult(expected_table, expected_error)
        expected.sanitize_in_place()

        self.assertEqual(result.error, expected.error)
        assert_frame_equal(result.dataframe, expected.dataframe)

    def test_python_formula_int_output(self):
        self._test(
            pd.DataFrame({'A': [10, 20]}),
            {'syntax': 'python', 'formula_python': 'A*2'},
            pd.DataFrame({'A': [10, 20], 'R': [20, 40]})
        )

    def test_python_formula_str_output(self):
        self._test(
            pd.DataFrame({'A': [10, 20]}),
            {'syntax': 'python', 'formula_python': 'str(A) + "x"'},
            pd.DataFrame({'A': [10, 20], 'R': ['10x', '20x']})
        )

    def test_python_formula_empty_output_pval_makes_result(self):
        # empty out_column defaults to 'result'
        self._test(
            pd.DataFrame({'A': [1]}),
            {'syntax': 'python', 'formula_python': 'A*2', 'out_column': ''},
            pd.DataFrame({'A': [1], 'result': [2]})
        )

    def test_python_formula_missing_colname_makes_error(self):
        # formula with missing column name should error
        self._test(
            pd.DataFrame({'A': [1]}),
            {'syntax': 'python', 'formula_python': 'B*2'},
            expected_error="name 'B' is not defined"
        )

    def test_python_formula_cast_nonsane_output(self):
        self._test(
            pd.DataFrame({'A': [1, 2]}),
            {'syntax': 'python', 'formula_python': '[A]'},
            pd.DataFrame({'A': [1, 2], 'R': ['[1]', '[2]']})
        )

    def test_python_spaces_to_underscores(self):
        # column names with spaces should be referenced with underscores in the
        # formula
        self._test(
            pd.DataFrame({'A b': [1, 2]}),
            {'syntax': 'python', 'formula_python': 'A_b*2'},
            pd.DataFrame({'A b': [1, 2], 'R': [2, 4]})
        )

    def test_excel_formula_no_output_col_name(self):
        # if no output column name specified, store to a column named 'result'
        self._test(
            pd.DataFrame({'A': [1, 2]}),
            {'formula_excel': '=A1*2', 'all_rows': True, 'out_column': ''},
            pd.DataFrame({'A': [1, 2], 'result': [2.0, 4.0]})
        )

    # --- Formulas which write to all rows ---
    def test_excel_all_rows_single_column(self):
        self._test(
            pd.DataFrame({'A': [1, 2]}),
            {'formula_excel': '=A1*2', 'all_rows': True},
            pd.DataFrame({'A': [1, 2], 'R': [2.0, 4.0]})
        )

    def test_excel_all_rows_column_range(self):
        self._test(
            pd.DataFrame({'A': [1, 2], 'B': [2, 3], 'C': [3, 4]}),
            {'formula_excel': '=SUM(A1:C1)', 'all_rows': True},
            pd.DataFrame({
                'A': [1, 2],
                'B': [2, 3],
                'C': [3, 4],
                'R': [6, 9],
            })
        )

    def test_excel_text_formula(self):
        self._test(
            pd.DataFrame({'A': ['foo', 'bar']}),
            {'formula_excel': '=LEFT(A1, 2)', 'all_rows': True},
            pd.DataFrame({'A': ['foo', 'bar'], 'R': ['fo', 'ba']})
        )

    # --- Formulas which write only to a single row ---
    def test_excel_divide_two_rows(self):
        self._test(
            pd.DataFrame({'A': [1, 2]}),
            {'formula_excel': '=A1/A2', 'all_rows': False},
            pd.DataFrame({'A': [1, 2], 'R': [0.5, np.nan]})
        )

    def test_excel_add_two_columns(self):
        self._test(
            pd.DataFrame({'A': [1, 2], 'B': [2, 3]}),
            {'formula_excel': '=A1+B1', 'all_rows': False},
            pd.DataFrame({'A': [1, 2], 'B': [2, 3], 'R': [3, np.nan]})
        )

    def test_excel_sum_column(self):
        self._test(
            pd.DataFrame({'A': [1, 2, 3]}),
            {'formula_excel': '=SUM(A2:A3)', 'all_rows': False},
            pd.DataFrame({'A': [1, 2, 3], 'R': [5, np.nan, np.nan]})
        )

    def test_excel_error_missing_row_number(self):
        self._test(
            pd.DataFrame({'A': [1, 2]}),
            {'formula_excel': '=A*2', 'all_rows': True},
            expected_error='Bad cell reference A'
        )

    def test_excel_error_missing_row_number_in_range(self):
        self._test(
            pd.DataFrame({'A': [1, 2], 'B': [2, 3]}),
            {'formula_excel': '=SUM(A:B)', 'all_rows': True},
            expected_error=(
                'Excel formulas can only reference '
                'the first row when applied to all rows'
            )
        )

    def test_excel_error_reference_row_other_than_1_with_all_rows(self):
        self._test(
            pd.DataFrame({'A': [1, 2]}),
            {'formula_excel': '=A2*2', 'all_rows': True},
            expected_error=(
                'Excel formulas can only reference '
                'the first row when applied to all rows'
            )
        )

    def test_excel_error_syntax(self):
        self._test(
            pd.DataFrame({'A': [1, 2]}),
            {'formula_excel': '=SUM B>', 'all_rows': False},
            expected_error=(
                # The "%s" is built in to the formulas module. TODO file bugrep
                "Couldn't parse formula: Not a valid formula:\n%s"
            )
        )

    def test_excel_error_out_of_range_columns(self):
        self._test(
            pd.DataFrame({'A': [1, 2]}),
            {'formula_excel': '=SUM(A1:B1)', 'all_rows': True},
            expected_error=(
                'index 1 is out of bounds for axis 0 with size 1'
            )
        )

    def test_excel_error_out_of_range_rows(self):
        self._test(
            pd.DataFrame({'A': [1, 2]}),
            {'formula_excel': '=SUM(A1:A3)', 'all_rows': False},
            # Just ignore missing rows
            pd.DataFrame({'A': [1, 2], 'R': [3, np.nan]})
        )

    def test_excel_error_row_0(self):
        self._test(
            pd.DataFrame({'A': [1, 2]}),
            {'formula_excel': '=A0*2', 'all_rows': False},
            expected_error='Invalid cell range: A0'
        )
