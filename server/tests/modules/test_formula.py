from django.test import TestCase
from server.views.WfModule import make_render_json
from server.tests.utils import *

# ---- Formula ----

class FormulaTests(LoggedInTestCase):
    def setUp(self):
        super(FormulaTests, self).setUp()  # log in
        formula_def = load_module_def('formula')
        self.wfmodule = load_and_add_module(create_testdata_workflow(), formula_def)
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

        response = self.client.get('/api/wfmodules/%d/render' % self.wfmodule.id)
        self.wfmodule.refresh_from_db()
        self.assertEqual(self.wfmodule.status, WfModule.READY)
        self.assertEqual(response.content, make_render_json(table))

        # empty result parameter should produce 'result'
        self.rpval.value = ''
        self.rpval.save()
        table = mock_csv_table.copy()
        table['result'] = table['Amount']*2.0  # need the .0 as output is going to be floating point
        response = self.client.get('/api/wfmodules/%d/render' % self.wfmodule.id)
        self.wfmodule.refresh_from_db()
        self.assertEqual(self.wfmodule.status, WfModule.READY)
        self.assertEqual(response.content, make_render_json(table))

        # formula with missing column name should error
        self.fpval.value = 'xxx*2'
        self.fpval.save()
        response = self.client.get('/api/wfmodules/%d/render' % self.wfmodule.id)
        self.wfmodule.refresh_from_db()
        self.assertEqual(self.wfmodule.status, WfModule.ERROR)
        self.assertEqual(response.content, make_render_json(pd.DataFrame()))
