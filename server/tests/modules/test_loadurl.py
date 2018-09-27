import asyncio
from collections import OrderedDict
import io
import json
import os
import tempfile
import unittest
from unittest.mock import patch
from asgiref.sync import async_to_sync
from django.conf import settings
import requests
import pandas as pd
from server.modules.loadurl import LoadURL
from server.modules.types import ProcessResult
from server.tests.utils import mock_xlsx_path

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


def respond(str_or_bytes, content_type):
    def r(*args, **kwargs):
        if isinstance(str_or_bytes, str):
            return mock_text_response(str_or_bytes, content_type)
        else:
            return mock_bytes_response(str_or_bytes, content_type)

    return r


def mock_404_response(text):
    def r(*args, **kwargs):
        response = requests.Response()
        response.encoding = 'utf-8'
        response.headers['Content-Type'] = 'text/plain; charset=utf-8'
        response.raw = io.BytesIO(text.encode('utf-8'))
        response.reason = 'Not Found'
        response.status_code = 404
        return response
    return r


class MockWfModule:
    def __init__(self, **kwargs):
        self.url = kwargs.get('url', '')
        self.has_header = kwargs.get('has_header', True)

    def get_param_string(self, param):
        return getattr(self, param)

    def get_param_checkbox(self, param):
        return getattr(self, param)

    def retrieve_fetched_table(self):
        return self.fetched_table


def run_event(wf_module):
    async_to_sync(LoadURL.event)(wf_module)


class LoadFromURLTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.wf_module = MockWfModule()

        self.commit_result_patch = \
            patch('server.modules.moduleimpl.ModuleImpl.commit_result')
        self.commit_result = self.commit_result_patch.start()
        # Mock commit_result by making it return None, asynchronously
        future = asyncio.Future()
        future.set_result(None)
        self.commit_result.return_value = future

    def tearDown(self):
        self.commit_result_patch.stop()

        super().tearDown()

    def test_load_csv(self):
        self.wf_module.url = 'http://test.com/the.csv'

        # success case
        with patch('requests.get', respond(mock_csv_text, 'text/csv')):
            run_event(self.wf_module)

        self.commit_result.assert_called_with(
            self.wf_module,
            ProcessResult(mock_csv_table)
        )

    def test_load_invalid_csv(self):
        # malformed CSV should put module in error state
        self.wf_module.url = 'http://test.com/the.csv'
        with patch('requests.get', respond('a,b\n"1', 'text/csv')):
            run_event(self.wf_module)

        self.commit_result.assert_called_with(
            self.wf_module,
            ProcessResult(error=(
                'Error tokenizing data. C error: EOF inside string '
                'starting at line 1'
            ))
        )

    def test_load_csv_use_ext_given_bad_content_type(self):
        # return text/plain type and rely on filename detection, as
        # https://raw.githubusercontent.com/ does
        self.wf_module.url = \
            'https://raw.githubusercontent.com/user/repo/branch/the.csv'

        with patch('requests.get', respond(mock_csv_text, 'text/plain')):
            run_event(self.wf_module)

        self.commit_result.assert_called_with(
            self.wf_module,
            ProcessResult(mock_csv_table)
        )

    def test_load_json(self):
        self.wf_module.url = 'http://test.com/the.json'

        # use a complex example with nested data
        fname = os.path.join(settings.BASE_DIR,
                             'server/tests/test_data/sfpd.json')
        sfpd_json = open(fname).read()
        # OrderedDict otherwise cols get sorted
        sfpd_table = pd.DataFrame(json.loads(sfpd_json,
                                             object_pairs_hook=OrderedDict))

        expected = ProcessResult(sfpd_table)
        expected.sanitize_in_place()

        with patch('requests.get', respond(sfpd_json, 'application/json')):
            run_event(self.wf_module)

        self.commit_result.assert_called_with(self.wf_module, expected)

    def test_load_json_invalid_json(self):
        self.wf_module.url = 'http://test.com/the.json'

        # malformed json should put module in error state
        with patch('requests.get', respond('not json', 'application/json')):
            run_event(self.wf_module)

        self.commit_result.assert_called_with(
            self.wf_module,
            ProcessResult(error='Expecting value: line 1 column 1 (char 0)')
        )

    def test_load_xlsx(self):
        self.wf_module.url = 'http://test.com/the.xlsx'

        xlsx_bytes = open(mock_xlsx_path, "rb").read()
        xlsx_table = pd.read_excel(mock_xlsx_path)
        response = respond(xlsx_bytes, XLSX_MIME_TYPE)

        with patch('requests.get', response):
            run_event(self.wf_module)

        self.commit_result.assert_called_with(self.wf_module,
                                              ProcessResult(xlsx_table))

    def test_load_xlsx_bad_content(self):
        self.wf_module.url = 'http://test.com/the.xlsx'

        response = respond(b'hi', XLSX_MIME_TYPE)

        # malformed file  should put module in error state
        with patch('requests.get', response):
            run_event(self.wf_module)

        self.commit_result.assert_called_with(
            self.wf_module,
            ProcessResult(error=(
                "Error reading Excel file: Unsupported format, or corrupt "
                "file: Expected BOF record; found b'hi'"
            ))
        )

    def test_load_404(self):
        self.wf_module.url = 'http://test.com/the.csv'

        # 404 error should put module in error state
        with patch('requests.get', mock_404_response('Foobar')):
            run_event(self.wf_module)

        self.commit_result.assert_called_with(
            self.wf_module,
            ProcessResult(error='Error 404 fetching url')
        )

    def test_bad_url(self):
        self.wf_module.url = 'not a url'

        run_event(self.wf_module)

        self.commit_result.assert_called_with(
            self.wf_module,
            ProcessResult(error='Invalid URL')
        )
