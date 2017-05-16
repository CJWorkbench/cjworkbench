from django.test import TestCase
from rest_framework import status
from server.models import Module, WfModule, Workflow, ParameterSpec, ParameterVal
from server.tests.utils import *
from server.execute import execute_wfmodule
import requests_mock
import pandas as pd
import io
import os
import json

mock_json_text = '[ {"Month" : "Jan", "Amount": 10},\n {"Month" : "Feb", "Amount": 20} ]'
mock_json_table = pd.DataFrame(json.loads(mock_json_text))

mock_json_path = 'data.series[1]'
mock_json_path_text = '{"data": {"junk":"aaa", "series": [ {"key":"value"}, [ {"Month" : "Jan", "Amount": 10},\n {"Month" : "Feb", "Amount": 20} ] ] } }'

mock_xslx_path = os.path.join(settings.BASE_DIR, 'server/tests/modules/test.xlsx')

# ---- LoadURL ----

class LoadFromURLTests(LoggedInTestCase):
    def setUp(self):
        super(LoadFromURLTests, self).setUp()  # log in
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


