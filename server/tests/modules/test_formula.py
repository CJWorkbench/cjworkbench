from django.test import TestCase
from server.execute import execute_nocache
from server.tests.utils import *
from server.modules.formula import letter_ref_to_number

# ---- Formula ----
mock_csv_text = 'Month,Amount,Amount2,Name\nJan,10,11,Alicia Aliciason\nFeb,666,333,Fred Frederson'
mock_csv_table = pd.read_csv(io.StringIO(mock_csv_text))

class FormulaTests(LoggedInTestCase):
    def setUp(self):
        super(FormulaTests, self).setUp()  # log in
        self.wfmodule = load_and_add_module('formula', workflow=create_testdata_workflow(csv_text=mock_csv_text))

        self.syntax_pval = get_param_by_id_name('syntax')
        self.excel_pval = get_param_by_id_name('formula_excel')
        self.python_pval = get_param_by_id_name('formula_python')
        self.rpval = get_param_by_id_name('out_column')

    def test_python_formula(self):
        # set up a formula to double the Amount column
        self.python_pval.set_value('Amount*2')
        self.python_pval.save()
        self.syntax_pval.set_value(1)
        self.syntax_pval.save()
        self.rpval.value= 'output'
        self.rpval.save()
        table = mock_csv_table.copy()
        table['output'] = table['Amount']*2
        table['output'] = table['output'].astype(object)

        out = execute_nocache(self.wfmodule)
        self.wfmodule.refresh_from_db()
        self.assertEqual(self.wfmodule.status, WfModule.READY)
        self.assertTrue(out.equals(table))

        # empty result parameter should produce 'result'
        self.rpval.set_value('')
        self.rpval.save()
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


    def test_excel_formula(self):
        # We have custom range handling logic and syntax, so this test exercises many types of ranges
        self.syntax_pval.set_value(0)
        self.syntax_pval.save()
        table = mock_csv_table.copy()

        # simple single-column reference
        self.excel_pval.set_value('=B*2')
        self.excel_pval.save()

        # empty result parameter should produce 'result'
        self.rpval.value = ''
        self.rpval.save()
        table['result'] = table['Amount'] * 2
        table['result'] = table['result'].astype(object)
        out = execute_nocache(self.wfmodule)
        self.wfmodule.refresh_from_db()
        self.assertEqual(self.wfmodule.status, WfModule.READY)
        self.assertTrue(out.equals(table))

        # simple single-column reference
        self.excel_pval.set_value('=B*2')
        self.excel_pval.save()

        table = mock_csv_table.copy()
        self.rpval.value = 'output'
        self.rpval.save()

        table['output'] = table['Amount'] * 2
        table['output'] = table['output'].astype(object)
        out = execute_nocache(self.wfmodule)
        self.wfmodule.refresh_from_db()
        self.assertEqual(self.wfmodule.status, WfModule.READY)
        self.assertTrue(out.equals(table))

        # simple single-column reference
        self.excel_pval.set_value('=B1*2')
        self.excel_pval.save()
        out = execute_nocache(self.wfmodule)
        self.wfmodule.refresh_from_db()
        self.assertEqual(self.wfmodule.status, WfModule.READY)
        self.assertTrue(out.equals(table))

        # formula with range should grab the right values and compute them
        self.excel_pval.set_value('=SUM(B:C)')
        self.excel_pval.save()
        table['output'] = table['Amount'] + table['Amount2']
        table['output'] = table['output'].astype(object)
        out = execute_nocache(self.wfmodule)
        self.wfmodule.refresh_from_db()
        self.assertEqual(self.wfmodule.status, WfModule.READY)
        self.assertTrue(out.equals(table))

        # same formula with B1 and C1 should still work
        self.excel_pval.set_value('=SUM(B1:C1)')
        self.excel_pval.save()
        out = execute_nocache(self.wfmodule)
        self.wfmodule.refresh_from_db()
        self.assertEqual(self.wfmodule.status, WfModule.READY)
        self.assertTrue(out.equals(table))

        # same formula with B and C1 should still work
        self.excel_pval.set_value('=SUM(B:C1)')
        self.excel_pval.save()
        out = execute_nocache(self.wfmodule)
        self.wfmodule.refresh_from_db()
        self.assertEqual(self.wfmodule.status, WfModule.READY)
        self.assertTrue(out.equals(table))

        # text formula
        self.excel_pval.set_value('=LEFT(D,5)')
        self.excel_pval.save()
        table['output'] = table['Name'].apply(lambda x: x[:5])
        table['output'] = table['output'].astype(object)
        out = execute_nocache(self.wfmodule)
        self.wfmodule.refresh_from_db()
        self.assertEqual(self.wfmodule.status, WfModule.READY)
        self.assertTrue(out.equals(table))

        # bad formula should produce error
        self.excel_pval.set_value('=SUM B:C')
        self.excel_pval.save()
        out = execute_nocache(self.wfmodule)
        self.wfmodule.refresh_from_db()
        self.assertEqual(self.wfmodule.status, WfModule.ERROR)
        self.assertTrue(out.equals(mock_csv_table))  # NOP on error

        # out of range selector should produce error
        self.excel_pval.set_value('=SUM(B:ZZ)')
        self.excel_pval.save()
        out = execute_nocache(self.wfmodule)
        self.wfmodule.refresh_from_db()
        self.assertEqual(self.wfmodule.status, WfModule.ERROR)
        self.assertTrue(out.equals(mock_csv_table))  # NOP on error

        # selector with a 0 should produce an error
        self.excel_pval.set_value('=SUM(B0)')
        self.excel_pval.save()
        out = execute_nocache(self.wfmodule)
        self.wfmodule.refresh_from_db()
        self.assertEqual(self.wfmodule.status, WfModule.ERROR)
        self.assertTrue(out.equals(mock_csv_table))  # NOP on error
