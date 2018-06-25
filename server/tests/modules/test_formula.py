from django.test import TestCase
from server.execute import execute_nocache
from server.tests.utils import *
from server.modules.formula import letter_ref_to_number
from server.sanitizedataframe import sanitize_dataframe

# ---- Formula ----
mock_csv_text = 'Month,Amount,Amount2,Name\nJan,10,11,Alicia Aliciason\nFeb,666,333,Fred Frederson'
mock_csv_table = pd.read_csv(io.StringIO(mock_csv_text))

class FormulaTests(LoggedInTestCase):
    def setUp(self):
        super(FormulaTests, self).setUp()  # log in
        self.wfmodule = load_and_add_module('formula', workflow=create_testdata_workflow(csv_text=mock_csv_text))

        self.syntax_pval = get_param_by_id_name('syntax')
        self.excel_pval = get_param_by_id_name('formula_excel')
        self.all_rows_pval = get_param_by_id_name('all_rows')
        self.python_pval = get_param_by_id_name('formula_python')
        self.outcol_pval = get_param_by_id_name('out_column')
        self.outcol_pval.value= 'output'
        self.outcol_pval.save()

    def test_python_formula(self):
        # set up a formula to double the Amount column
        self.python_pval.set_value('Amount*2')
        self.python_pval.save()
        self.syntax_pval.set_value(1)
        self.syntax_pval.save()
        table = mock_csv_table.copy()
        table['output'] = table['Amount']*2
        table['output'] = table['output'].astype(object)

        out = execute_nocache(self.wfmodule)
        self.wfmodule.refresh_from_db()
        self.assertEqual(self.wfmodule.status, WfModule.READY)
        self.assertTrue(out.equals(table))

        # empty result parameter should produce 'result'
        self.outcol_pval.set_value('')
        self.outcol_pval.save()
        table = mock_csv_table.copy()
        table['result'] = table['Amount']*2
        table['result'] = table['result'].astype(object)
        out = execute_nocache(self.wfmodule)
        self.wfmodule.refresh_from_db()
        self.assertEqual(self.wfmodule.status, WfModule.READY)
        self.assertTrue(out.equals(table))

        # formula with missing column name should error
        self.python_pval.set_value('xxx*2')
        self.python_pval.save()
        out = execute_nocache(self.wfmodule)
        self.wfmodule.refresh_from_db()
        self.assertEqual(self.wfmodule.status, WfModule.ERROR)
        self.assertTrue(out.equals(mock_csv_table))  # NOP on error


    def test_spaces_to_underscores(self):
        # column names with spaces should be referenced with underscores in the formula
        underscore_csv = 'Month,The Amount,Name\nJan,10,Alicia Aliciason\nFeb,666,Fred Frederson'
        underscore_table = pd.read_csv(io.StringIO(underscore_csv))

        workflow = create_testdata_workflow(underscore_csv)
        wfm = load_and_add_module('formula', workflow=workflow)
        pval = get_param_by_id_name('formula_python', wf_module=wfm)
        pval.set_value('The_Amount*2')
        sval = get_param_by_id_name('syntax', wf_module=wfm)
        sval.set_value(1)

        out = execute_nocache(wfm)

        table = underscore_table.copy()
        table['formula output'] = table['The Amount']*2
        table['formula output'] = table['formula output'].astype(object)
        self.assertTrue(out.equals(table))


    def test_ref_to_number(self):
        self.assertTrue(letter_ref_to_number('A') == 0)
        self.assertTrue(letter_ref_to_number('AA') == 26)
        self.assertTrue(letter_ref_to_number('AZ') == 51)
        self.assertTrue(letter_ref_to_number('BA') == 52)


    def _set_excel_formula(self, formula, all_rows=True):
        self.syntax_pval.set_value(0)
        self.syntax_pval.save()
        self.all_rows_pval.set_value(all_rows)
        self.all_rows_pval.save()
        self.excel_pval.set_value(formula)
        self.excel_pval.save()


    def _assert_module_result(self, correct_result, correct_status=WfModule.READY):
        out = execute_nocache(self.wfmodule)
        self.wfmodule.refresh_from_db()
        self.assertEqual(self.wfmodule.status, correct_status)
        self.assertTrue(out.equals(correct_result))


    def test_excel_formula_no_output_col_name(self):
        # if no output column name specified, store to a column named 'result'
        self._set_excel_formula('=B1*2', all_rows=True)
        self.outcol_pval.value = ''
        self.outcol_pval.save()

        table = mock_csv_table.copy()
        table['result'] = table['Amount'] * 2
        table['result'] = table['result'].astype(object)

        self._assert_module_result(table)


    def test_excel_range_types(self):
        # We have custom range handling logic and syntax, so this test exercises many types of ranges
        # All of these tests operate on all rows
        table = mock_csv_table.copy()
        table['output'] = table['Amount'] * 2
        table['output'] = table['output'].astype(object)

        # formula: single-column reference
        self._set_excel_formula('=B1*2', all_rows=True)
        self._assert_module_result(table)

        # formula: horizontal range
        self._set_excel_formula('=SUM(B1:C1)', all_rows=True)
        table['output'] = table['Amount'] + table['Amount2']
        table['output'] = table['output'].astype(object)
        self._assert_module_result(table)


    def test_excel_text_formula(self):
        self._set_excel_formula('=LEFT(D1,5)', all_rows=True)
        table = mock_csv_table.copy()
        table['output'] = table['Name'].apply(lambda x: x[:5])
        table['output'] = table['output'].astype(object)
        self._assert_module_result(table)


    def test_bad_excel_formulas(self):
        # column without row number
        self._set_excel_formula('=B*2', all_rows=True)
        self._assert_module_result(mock_csv_table, WfModule.ERROR)

        # also without row numbers
        self._set_excel_formula('=SUM(B:C)', all_rows=True)
        self._assert_module_result(mock_csv_table, WfModule.ERROR)

        # attempted reference to another row
        self._set_excel_formula('=B2*2', all_rows=True)
        self._assert_module_result(mock_csv_table, WfModule.ERROR)

        # bad formula should produce error
        self._set_excel_formula('=SUM B:C', all_rows=True)
        self._assert_module_result(mock_csv_table, WfModule.ERROR)

        # out of range selector should produce error
        self._set_excel_formula('=SUM(B:ZZ)', all_rows=True)
        self._assert_module_result(mock_csv_table, WfModule.ERROR)

        # selector with a 0 should produce an error
        self._set_excel_formula('=SUM(B0)', all_rows=True)
        self._assert_module_result(mock_csv_table, WfModule.ERROR)


    # Formula which writes only to a single row
    def test_excel_single_row(self):
        self._set_excel_formula('=SUM(B1:B2)', all_rows=False)
        table = mock_csv_table.copy()
        table['output'] = pd.Series([sum(table['Amount']), None], dtype=object)
        sanitize_dataframe(table)  # force representation of [int,None] to be same as what we get from rendering
                                   # (could be [10, None] or ["10",None]  or [10.0, NaN])
        self._assert_module_result(table)
