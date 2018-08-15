from collections import OrderedDict
import io
import json
import os
import tempfile
from unittest.mock import patch
from django.conf import settings
from django.test import override_settings
import requests
import pandas as pd
from server.execute import execute_wfmodule
from server.models import ParameterVal
from server.modules.types import ProcessResult
from server.tests.utils import LoggedInTestCase, load_and_add_module, \
        mock_xlsx_path

XLSX_MIME_TYPE = \
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

mock_csv_text = 'Month,Amount\nJan,10\nFeb,20'
mock_csv_raw = io.BytesIO(mock_csv_text.encode('utf-8'))
mock_csv_table = pd.read_csv(mock_csv_raw)
mock_csv_text2 = \
        'Month,Amount,Name\nJan,10,Alicia Aliciason\nFeb,666,Fred Frederson'
mock_csv_raw2 = io.BytesIO(mock_csv_text2.encode('utf-8'))
mock_csv_table2 = pd.read_csv(mock_csv_raw2)


def mock_text_response(text, content_type):
    response = requests.Response()
    response.encoding = 'utf-8'
    response.headers['Content-Type'] = content_type
    # In requests, `response.raw` does not behave like a file-like object
    # as we would expect. But it does happen to give us a correct
    # `response.content` in the code that uses that.
    response.raw = io.BytesIO(text.encode('utf-8'))
    response.reason = 'OK'
    response.status_code = 200
    return response


def mock_bytes_response(b, content_type):
    response = requests.Response()
    response.headers['Content-Type'] = content_type
    response.raw = io.BytesIO(b)
    response.reason = 'OK'
    response.status_code = 200
    return response


def mock_404_response(text):
    response = requests.Response()
    response.encoding = 'utf-8'
    response.headers['Content-Type'] = 'text/plain; charset=utf-8'
    response.raw = io.BytesIO(text.encode('utf-8'))
    response.reason = 'Not Found'
    response.status_code = 404
    return response


# ---- LoadURL ----
@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class LoadFromURLTests(LoggedInTestCase):
    def setUp(self):
        super().setUp()  # log in
        self.wfmodule = load_and_add_module('loadurl')

        # save references to our parameter values so we can tweak them later
        self.url_pval = ParameterVal.objects.get(parameter_spec__id_name='url')
        self.fetch_pval = ParameterVal.objects.get(
            parameter_spec__id_name='version_select'
        )

    # send fetch event to button to load data
    def press_fetch_button(self):
        self.client.post('/api/parameters/%d/event' % self.fetch_pval.id)
        self.wfmodule.refresh_from_db()  # last_relevant_delta_id changed

    def test_load_csv(self):
        url = 'http://test.com/the.csv'
        self.url_pval.set_value(url)
        self.url_pval.save()

        # should be no data saved yet, no Deltas on the workflow
        self.assertIsNone(self.wfmodule.get_fetched_data_version())
        self.assertIsNone(self.wfmodule.retrieve_fetched_table())
        self.assertIsNone(self.wfmodule.workflow.last_delta)

        # success case
        with patch('requests.get') as get:
            get.return_value = mock_text_response(mock_csv_text, 'text/csv')
            self.press_fetch_button()
            result = execute_wfmodule(self.wfmodule)
            self.assertEqual(result, ProcessResult(mock_csv_table))

            # should create a new data version on the WfModule, and a new delta
            # representing the change
            self.wfmodule.refresh_from_db()
            self.wfmodule.workflow.refresh_from_db()
            first_version = self.wfmodule.get_fetched_data_version()
            first_delta = self.wfmodule.workflow.last_delta
            first_check_time = self.wfmodule.last_update_check
            self.assertIsNotNone(first_version)
            self.assertIsNotNone(first_delta)

        # retrieving exactly the same data should not create a new data version
        # or delta, should update check time
        with patch('requests.get') as get:
            get.return_value = mock_text_response(mock_csv_text, 'text/csv')
            self.press_fetch_button()

            self.wfmodule.refresh_from_db()
            self.wfmodule.workflow.refresh_from_db()
            self.assertEqual(self.wfmodule.get_fetched_data_version(),
                             first_version)
            self.assertEqual(self.wfmodule.workflow.last_delta, first_delta)
            second_check_time = self.wfmodule.last_update_check
            self.assertNotEqual(second_check_time, first_check_time)

        # Retrieving different data should create a new data version and delta
        with patch('requests.get') as get:
            get.return_value = mock_text_response(mock_csv_text2, 'text/csv')
            self.press_fetch_button()
            result = execute_wfmodule(self.wfmodule)
            self.assertEqual(result, ProcessResult(mock_csv_table2))

            self.wfmodule.refresh_from_db()
            self.wfmodule.workflow.refresh_from_db()
            self.assertNotEqual(self.wfmodule.get_fetched_data_version(),
                                first_version)
            self.assertNotEqual(self.wfmodule.workflow.last_delta, first_delta)
            self.assertNotEqual(self.wfmodule.last_update_check,
                                second_check_time)

        # malformed CSV should put module in error state
        with patch('requests.get') as get:
            get.return_value = mock_text_response('a,b\n"1', 'text/csv')
            self.press_fetch_button()
            self.wfmodule.refresh_from_db()
            self.assertEqual(
                self.wfmodule.fetch_error,
                'Error tokenizing data. C error: EOF inside string '
                'starting at line 1'
            )

    def test_load_csv_bad_content_type(self):
        # return text/plain type and rely on filename detection, as
        # https://raw.githubusercontent.com/ does
        url = 'https://raw.githubusercontent.com/user/repo/branch/the.csv'
        self.url_pval.set_value(url)
        self.url_pval.save()
        with patch('requests.get') as get:
            get.return_value = mock_text_response(mock_csv_text, 'text/plain')
            self.press_fetch_button()
            result = execute_wfmodule(self.wfmodule)
            self.assertEqual(result, ProcessResult(mock_csv_table))

    def test_load_json(self):
        url = 'http://test.com/the.json'
        self.url_pval.set_value(url)
        self.url_pval.save()

        # use a complex example with nested data
        fname = os.path.join(settings.BASE_DIR,
                             'server/tests/test_data/sfpd.json')
        sfpd_json = open(fname).read()
        # OrderedDict otherwise cols get sorted
        sfpd_table = pd.DataFrame(json.loads(sfpd_json,
                                             object_pairs_hook=OrderedDict))
        expected = ProcessResult(sfpd_table)
        expected.sanitize_in_place()

        with patch('requests.get') as get:
            get.return_value = mock_text_response(sfpd_json,
                                                  'application/json')
            self.press_fetch_button()
            result = execute_wfmodule(self.wfmodule)
            self.assertEqual(result, expected)

    def test_load_json_bad_content(self):
        url = 'http://test.com/the.json'
        self.url_pval.set_value(url)
        self.url_pval.save()

        # malformed json should put module in error state
        with patch('requests.get') as get:
            get.return_value = mock_text_response('not json',
                                                  'application/json')
            self.press_fetch_button()
            self.wfmodule.refresh_from_db()
            self.assertEqual(self.wfmodule.fetch_error,
                             'Expecting value: line 1 column 1 (char 0)')

    def test_load_xlsx(self):
        url = 'http://test.com/the.xlsx'
        self.url_pval.set_value(url)
        self.url_pval.save()

        xlsx_bytes = open(mock_xlsx_path, "rb").read()
        xlsx_table = pd.read_excel(mock_xlsx_path)

        with patch('requests.get') as get:
            get.return_value = mock_bytes_response(xlsx_bytes, XLSX_MIME_TYPE)
            self.press_fetch_button()
            result = execute_wfmodule(self.wfmodule)
            self.assertEqual(result, ProcessResult(xlsx_table))

    def test_load_xlsx_bad_content(self):
        url = 'http://test.com/the.xlsx'
        self.url_pval.set_value(url)
        self.url_pval.save()

        # malformed file  should put module in error state
        with patch('requests.get') as get:
            get.return_value = mock_bytes_response(b'hi', XLSX_MIME_TYPE)
            self.press_fetch_button()
            self.wfmodule.refresh_from_db()
            self.assertEqual(
                self.wfmodule.fetch_error,
                "Error reading Excel file: Unsupported format, or corrupt "
                "file: Expected BOF record; found b'hi'"
            )

    def test_load_404(self):
        url = 'http://test.com/the.csv'
        self.url_pval.set_value(url)
        self.url_pval.save()

        # 404 error should put module in error state
        with patch('requests.get') as get:
            get.return_value = mock_404_response('Foobar')
            self.press_fetch_button()
            self.wfmodule.refresh_from_db()
            self.assertEqual(self.wfmodule.fetch_error,
                             'Error 404 fetching url')

    def test_bad_url(self):
        url = 'not a url'
        self.url_pval.set_value(url)
        self.url_pval.save()

        self.press_fetch_button()
        self.wfmodule.refresh_from_db()
        self.assertEqual(self.wfmodule.fetch_error, 'Invalid URL')
