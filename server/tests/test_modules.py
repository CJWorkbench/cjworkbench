from django.test import TestCase
from rest_framework import status
from server.models import Module, WfModule, Workflow, ParameterSpec, ParameterVal
from server.tests.utils import *
from server.initmodules import load_module_from_dict
import pandas as pd
import io


mock_csv_text = 'Month,Amount\nJan,10\nFeb,20'


# setup a workflow with some test data loaded into a PasteCSV module
# returns workflow
def createMockWorkflow():
    csv_module = add_new_module('Module 1', 'pastecsv')
    pspec = add_new_parameter_spec(csv_module, 'csv', ParameterSpec.TEXT)
    workflow = add_new_workflow('Workflow 1')
    wfmodule = add_new_wf_module(workflow, csv_module, 0)
    wfmodule.create_default_parameters()
    pval = ParameterVal.objects.get(parameter_spec=pspec)
    pval.text = mock_csv_text
    pval.save()

    return workflow


class PasteCSVTests(TestCase):
    def setUp(self):
        self.workflow = createMockWorkflow()
        self.wf_module = WfModule.objects.all().first()

    def test_csv(self):
        response = self.client.get('/api/wfmodules/%d/render' % self.wf_module.id)
        table = pd.read_csv(io.StringIO(mock_csv_text))
        self.assertEqual(response.content, table_to_content(table))


class FormulaTests(TestCase):
    def setUp(self):
        self.workflow = createMockWorkflow()
        formula_def =  {
            "name": "Formula",
            "id_name": "formula",
            "parameters": [
                {
                    "name": "Formula",
                    "id_name": "formula",
                    "type": "string",
                    "default": ""
                },
                {
                    "name": "Output Column",
                    "id_name": "out_column",
                    "type": "string",
                    "default": "result"
                }
            ]
        }
        self.formula_module = load_module_from_dict(formula_def)
        self.wfmodule = add_new_wf_module(self.workflow, self.formula_module, 1) # 1 = order after CSV
        self.wfmodule.create_default_parameters()
        formula_pspec = ParameterSpec.objects.get(id_name='formula')
        self.fpval = ParameterVal.objects.get(parameter_spec=formula_pspec)
        output_pspec = ParameterSpec.objects.get(id_name='out_column')
        self.rpval = ParameterVal.objects.get(parameter_spec=output_pspec)

    def test_formula(self):
        # set up a formula to double the Amount column
        self.fpval.string = 'Amount*2'
        self.fpval.save()
        self.rpval.string = 'output'
        self.rpval.save()
        table = pd.read_csv(io.StringIO(mock_csv_text))
        table['output'] = table['Amount']*2.0  # need the .0 as output is going to be floating point

        response = self.client.get('/api/wfmodules/%d/render' % self.wfmodule.id)
        self.wfmodule.refresh_from_db()
        self.assertEqual(self.wfmodule.status, WfModule.READY)
        self.assertEqual(response.content, table_to_content(table))

        # empty result parameter should produce 'result'
        self.rpval.string = ''
        self.rpval.save()
        table = pd.read_csv(io.StringIO(mock_csv_text))
        table['result'] = table['Amount']*2.0  # need the .0 as output is going to be floating point
        response = self.client.get('/api/wfmodules/%d/render' % self.wfmodule.id)
        self.wfmodule.refresh_from_db()
        self.assertEqual(self.wfmodule.status, WfModule.READY)
        self.assertEqual(response.content, table_to_content(table))

        # formula with missing column name should error
        self.fpval.string = 'xxx*2'
        self.fpval.save()
        response = self.client.get('/api/wfmodules/%d/render' % self.wfmodule.id)
        self.wfmodule.refresh_from_db()
        self.assertEqual(self.wfmodule.status, WfModule.ERROR)
        self.assertEqual(response.content, table_to_content(pd.DataFrame()))

