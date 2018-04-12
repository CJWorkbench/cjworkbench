from django.test import TestCase
from server.execute import execute_nocache
from server.tests.utils import *
from server.modules.formula import letter_ref_to_number

# ---- Formula ----

class FormulaTests(LoggedInTestCase):
    def setUp(self):
        super(FormulaTests, self).setUp()  # log in
        self.wfmodule = load_and_add_module('formula', workflow=create_testdata_workflow())
        formula_pspec = ParameterSpec.objects.get(id_name='formula')
        self.fpval = ParameterVal.objects.get(parameter_spec=formula_pspec)
        output_pspec = ParameterSpec.objects.get(id_name='out_column')
        self.rpval = ParameterVal.objects.get(parameter_spec=output_pspec)

    def test_formula(self):
        # set up a formula to double the Amount column
        self.fpval.value= 'Amount*2'
        self.fpval.save()
        self.rpval.value= 'output'
        self.rpval.save()
        table = mock_csv_table.copy()
        table['output'] = table['Amount']*2.0  # need the .0 as output is going to be floating point

        out = execute_nocache(self.wfmodule)
        self.wfmodule.refresh_from_db()
        self.assertEqual(self.wfmodule.status, WfModule.READY)
        self.assertTrue(out.equals(table))

        # empty result parameter should produce 'result'
        self.rpval.value = ''
        self.rpval.save()
        table = mock_csv_table.copy()
        table['result'] = table['Amount']*2.0  # need the .0 as output is going to be floating point
        out = execute_nocache(self.wfmodule)
        self.wfmodule.refresh_from_db()
        self.assertEqual(self.wfmodule.status, WfModule.READY)
        self.assertTrue(out.equals(table))

        # formula with missing column name should error
        self.fpval.value = 'xxx*2'
        self.fpval.save()
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
        pval = ParameterVal.objects.get(parameter_spec=ParameterSpec.objects.get(id_name='formula'), wf_module=wfm)
        pval.set_value('The_Amount*2')

        out = execute_nocache(wfm)

        table = underscore_table.copy()
        table['formula output'] = table['The Amount']*2.0  # need the .0 as output is going to be floating point
        self.assertTrue(out.equals(table))

    def test_ref_to_number(self):
        self.assertTrue(letter_ref_to_number('A') == 0)
        self.assertTrue(letter_ref_to_number('AA') == 26)
        self.assertTrue(letter_ref_to_number('AZ') == 51)
        self.assertTrue(letter_ref_to_number('BA') == 52)





