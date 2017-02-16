from django.test import TestCase
from django.conf import settings
from rest_framework import status
from server.models import Module, WfModule, Workflow, ParameterSpec, ParameterVal
from server.tests.utils import *
from server.initmodules import load_module_from_dict
import requests_mock
import pandas as pd
import io
import os
import json


mock_csv_text = 'Month,Amount\nJan,10\nFeb,20'
mock_csv_table = pd.read_csv(io.StringIO(mock_csv_text))

mock_json_text = '[ {"Month" : "Jan", "Amount": 10},\n {"Month" : "Feb", "Amount": 20} ]'
mock_json_table = pd.DataFrame(json.loads(mock_json_text))

mock_json_path = 'data.series[1]'
mock_json_path_text = '{"data": {"junk":"aaa", "series": [ {"key":"value"}, [ {"Month" : "Jan", "Amount": 10},\n {"Month" : "Feb", "Amount": 20} ] ] } }'

mock_xslx_path = os.path.join(settings.BASE_DIR, 'server/tests/test.xlsx')

# setup a workflow with some test data loaded into a PasteCSV module
# returns workflow
def create_testdata_workflow():
    csv_module = add_new_module('Module 1', 'pastecsv')
    pspec = add_new_parameter_spec(csv_module, 'csv', ParameterSpec.TEXT)
    workflow = add_new_workflow('Workflow 1')
    wfmodule = add_new_wf_module(workflow, csv_module, 0)
    wfmodule.create_default_parameters()
    pval = ParameterVal.objects.get(parameter_spec=pspec)
    pval.text = mock_csv_text
    pval.save()

    return workflow

# Load module spec from same place initmodules gets it, return dict
def load_module_def(filename):
    module_path = os.path.join(settings.BASE_DIR, 'config/modules')
    fullname = os.path.join(module_path, filename + '.json')
    with open(fullname) as json_data:
        d = json.load(json_data)
    return d


# Given a module spec, add it to a workflow. Create new workflow if null
# Returns WfModule
def load_and_add_module(workflow, module_spec):
    if not workflow:
        workflow = add_new_workflow('Workflow 1')

    module = load_module_from_dict(module_spec)
    wf_module = add_new_wf_module(workflow, module, 1)  # 1 = order after PasteCSV from create_mock_workflow
    wf_module.create_default_parameters()

    return wf_module



class PasteCSVTests(TestCase):
    def setUp(self):
        self.workflow = create_testdata_workflow()
        self.wf_module = WfModule.objects.all().first()

    def test_csv(self):
        response = self.client.get('/api/wfmodules/%d/render' % self.wf_module.id)
        table = pd.read_csv(io.StringIO(mock_csv_text))
        self.assertEqual(response.content, table_to_content(table))


class FormulaTests(TestCase):
    def setUp(self):
        formula_def = load_module_def('formula')
        self.wfmodule = load_and_add_module(create_testdata_workflow(), formula_def)
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
        table = mock_csv_table.copy()
        table['output'] = table['Amount']*2.0  # need the .0 as output is going to be floating point

        response = self.client.get('/api/wfmodules/%d/render' % self.wfmodule.id)
        self.wfmodule.refresh_from_db()
        self.assertEqual(self.wfmodule.status, WfModule.READY)
        self.assertEqual(response.content, table_to_content(table))

        # empty result parameter should produce 'result'
        self.rpval.string = ''
        self.rpval.save()
        table = mock_csv_table.copy()
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



class LoadFromURLTests(TestCase):
    def setUp(self):
        loadurl_def = load_module_def('loadurl')
        self.wfmodule = load_and_add_module(None, loadurl_def)

        # save references to our parameter values so we can tweak them later
        self.url_pval = ParameterVal.objects.get(parameter_spec=ParameterSpec.objects.get(id_name='url'))
        self.fetch_pval = ParameterVal.objects.get(parameter_spec=ParameterSpec.objects.get(id_name='fetch'))
        self.path_pval = ParameterVal.objects.get(parameter_spec=ParameterSpec.objects.get(id_name='json_path'))

    # send fetch event to button to load data
    def press_fetch_button(self):
        self.client.post('/api/parameters/%d/event' % self.fetch_pval.id, {'type': 'click'})

    # get rendered result
    def get_render(self):
        return self.client.get('/api/wfmodules/%d/render' % self.wfmodule.id)


    def test_load_csv(self):
        url = 'http://test.com/the.csv'
        self.url_pval.string = url
        self.url_pval.save()

        # success case
        with requests_mock.Mocker() as m:
            m.get(url, text=mock_csv_text, headers={'content-type':'text/csv'})
            self.press_fetch_button()
            response = self.get_render()
            self.assertEqual(response.content, table_to_content(mock_csv_table))

        # malformed CSV should put module in error state
        with requests_mock.Mocker() as m:
            m.get(url, text = 'a,b\n"1', headers={'content-type':'text/csv'})
            self.press_fetch_button()
            self.wfmodule.refresh_from_db()
            self.assertEqual(self.wfmodule.status, WfModule.ERROR)


    def test_load_json(self):
        url = 'http://test.com/the.json'
        self.url_pval.string = url
        self.url_pval.save()

        # success case
        with requests_mock.Mocker() as m:
            m.get(url, text=mock_json_text, headers={'content-type': 'application/json'})
            self.press_fetch_button()
            response = self.get_render()
            self.assertEqual(response.content, table_to_content(mock_json_table))

        # malformed json should put module in error state
        with requests_mock.Mocker() as m:
            m.get(url, text="there's just no way this is json", headers={'content-type': 'application/json'})
            self.press_fetch_button()
            self.wfmodule.refresh_from_db()
            self.assertEqual(self.wfmodule.status, WfModule.ERROR)

        # success using json path
        with requests_mock.Mocker() as m:
            self.path_pval.string = mock_json_path
            self.path_pval.save()
            m.get(url, text=mock_json_path_text, headers={'content-type': 'application/json'})
            self.press_fetch_button()
            response = self.get_render()
            self.assertEqual(response.content, table_to_content(mock_json_table))

        # bad json path should put module in error state
        with requests_mock.Mocker() as m:
            self.path_pval.string = 'hilarious'
            self.path_pval.save()
            m.get(url, text=mock_json_path_text, headers={'content-type': 'application/json'})
            self.press_fetch_button()
            self.wfmodule.refresh_from_db()
            self.assertEqual(self.wfmodule.status, WfModule.ERROR)


    def test_load_xlsx(self):
        url = 'http://test.com/the.xlsx'
        self.url_pval.string = url
        self.url_pval.save()

        xlsx_bytes = open(mock_xslx_path, "rb").read()
        xlsx_table = pd.read_excel(mock_xslx_path)

        # success case
        with requests_mock.Mocker() as m:
            m.get(url, content=xlsx_bytes, headers={'content-type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'})
            self.press_fetch_button()
            response = self.get_render()
            self.assertEqual(response.content, table_to_content(xlsx_table))

        # malformed file  should put module in error state
        with requests_mock.Mocker() as m:
            m.get(url, content=b"there's just no way this is xlsx", headers={'content-type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'})
            self.press_fetch_button()
            self.wfmodule.refresh_from_db()
            self.assertEqual(self.wfmodule.status, WfModule.ERROR)


    def test_load_404(self):
        url = 'http://test.com/the.csv'
        self.url_pval.string = url
        self.url_pval.save()

        # 404 error should put module in error state
        with requests_mock.Mocker() as m:
            m.get(url, text='Not Found', status_code=404)
            self.press_fetch_button()
            self.wfmodule.refresh_from_db()
            self.assertEqual(self.wfmodule.status, WfModule.ERROR)
