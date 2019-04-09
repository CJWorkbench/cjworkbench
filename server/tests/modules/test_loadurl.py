from collections import OrderedDict
import io
import json
import os
import unittest
from unittest.mock import patch
import aiohttp
from asgiref.sync import async_to_sync
from django.conf import settings
import pandas as pd
import requests
from cjworkbench.types import ProcessResult
from server.modules import loadurl
from server.tests.utils import mock_xlsx_path
from .util import MockParams

XLSX_MIME_TYPE = \
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

mock_csv_raw = b'Month,Amount\nJan,10\nFeb,20'
mock_csv_table = pd.DataFrame({
    'Month': ['Jan', 'Feb'],
    'Amount': [10, 20]
})


class fake_spooled_data_from_url:
    def __init__(self, data=b'', content_type='', charset='utf-8', error=None):
        self.data = io.BytesIO(data)
        self.headers = {'Content-Type': content_type}
        self.charset = charset
        self.error = error

    def __call__(self, *args, **kwargs):
        return self

    async def __aenter__(self):
        if self.error:
            raise self.error
        else:
            return (self.data, self.headers, self.charset)
        return self

    async def __aexit__(self, *args):
        return


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


P = MockParams.factory(url='', has_header=True)


def fetch(**kwargs):
    params = P(**kwargs)
    return async_to_sync(loadurl.fetch)(params)


class LoadUrlTests(unittest.TestCase):
    @patch('server.modules.utils.spooled_data_from_url',
           fake_spooled_data_from_url(mock_csv_raw, 'text/csv'))
    def test_load_csv(self):
        fetch_result = fetch(url='http://test.com/the.csv')
        self.assertEqual(fetch_result, ProcessResult(mock_csv_table))

    @patch('server.modules.utils.spooled_data_from_url',
           fake_spooled_data_from_url(b'a,b\n"1', 'text/csv'))
    def test_load_invalid_csv(self):
        fetch_result = fetch(url='http://test.com/the.csv')
        self.assertEqual(fetch_result, ProcessResult(error=(
            'Error tokenizing data. C error: EOF inside string '
            'starting at row 1'
        )))

    @patch('server.modules.utils.spooled_data_from_url',
           fake_spooled_data_from_url(mock_csv_raw, 'text/plain'))
    def test_load_csv_use_ext_given_bad_content_type(self):
        # return text/plain type and rely on filename detection, as
        # https://raw.githubusercontent.com/ does
        fetch_result = fetch(url='http://test.com/the.csv')
        self.assertEqual(fetch_result, ProcessResult(mock_csv_table))

    @patch('server.modules.utils.spooled_data_from_url',
           fake_spooled_data_from_url(mock_csv_raw, 'application/csv'))
    def test_load_csv_handle_nonstandard_mime_type(self):
        """
        Transform 'application/csv' into 'text/csv', etc.

        Sysadmins sometimes invent MIME types and we can infer exactly what
        they _mean_, even if they didn't say it.
        """
        fetch_result = fetch(url='http://test.com/the.data?format=csv&foo=bar')
        self.assertEqual(fetch_result, ProcessResult(mock_csv_table))

    def test_load_json(self):
        with patch('server.modules.utils.spooled_data_from_url',
                   fake_spooled_data_from_url(b'[{"A":1}]', 'application/json',
                                              'utf-8')):
            fetch_result = fetch(url='http://test.com/the.json')

        self.assertEqual(fetch_result, ProcessResult(pd.DataFrame({'A': [1]})))

    @patch('server.modules.utils.spooled_data_from_url',
           fake_spooled_data_from_url(b'not json', 'application/json'))
    def test_load_json_invalid_json(self):
        # malformed json should put module in error state
        fetch_result = fetch(url='http://test.com/the.json')

        self.assertEqual(fetch_result, ProcessResult(error=(
            'Invalid JSON (Unexpected character found when decoding \'null\')'
        )))

    def test_load_xlsx(self):
        with open(mock_xlsx_path, 'rb') as f:
            xlsx_bytes = f.read()
            xlsx_table = pd.read_excel(mock_xlsx_path)

        with patch('server.modules.utils.spooled_data_from_url',
                   fake_spooled_data_from_url(xlsx_bytes, XLSX_MIME_TYPE,
                                              None)):
            fetch_result = fetch(url='http://test.com/x.xlsx')

        self.assertEqual(fetch_result, ProcessResult(xlsx_table))

    @patch('server.modules.utils.spooled_data_from_url',
           fake_spooled_data_from_url(b'hi', XLSX_MIME_TYPE, None))
    def test_load_xlsx_bad_content(self):
        # malformed file  should put module in error state
        with patch('requests.get', respond(b'hi', XLSX_MIME_TYPE)):
            fetch_result = fetch(url='http://test.com/x.xlsx')

        self.assertEqual(fetch_result, ProcessResult(error=(
            "Error reading Excel file: Unsupported format, or corrupt "
            "file: Expected BOF record; found b'hi'"
        )))

    @patch('server.modules.utils.spooled_data_from_url',
           fake_spooled_data_from_url(
               error=aiohttp.ClientResponseError(None, None, status=404,
                                                 message='Not Found')
           ))
    def test_load_404(self):
        # 404 error should put module in error state
        fetch_result = fetch(url='http://example.org/x.csv')
        self.assertEqual(fetch_result, ProcessResult(
            error='Error from server: 404 Not Found'
        ))

    def test_bad_url(self):
        fetch_result = fetch(url='not a url')
        self.assertEqual(fetch_result,
                         ProcessResult(error='Invalid URL'))
