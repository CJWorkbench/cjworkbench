import os.path
import unittest
from unittest.mock import patch, Mock
import pandas as pd
from pandas.testing import assert_frame_equal
import requests.exceptions
from server import oauth
from server.modules import googlesheets
from .util import MockParams

# example_csv, example_tsv, example_xls, example_xlsx: same spreadsheet, four
# binary representations
example_csv = b'foo,bar\n1,2\n2,3'
example_tsv = b'foo\tbar\n1\t2\n2\t3'
with open(os.path.join(os.path.dirname(__file__), '..', 'test_data',
                       'example.xls'), 'rb') as f:
    example_xls = f.read()
with open(os.path.join(os.path.dirname(__file__), '..', 'test_data',
                       'example.xlsx'), 'rb') as f:
    example_xlsx = f.read()

expected_table = pd.DataFrame({
    'foo': [1, 2],
    'bar': [2, 3],
})


class MockResponse:
    def __init__(self, status_code, text):
        self.status_code = status_code

        if isinstance(text, str):
            self.text = text
            self.content = text.encode('utf-8')
        else:
            self.content = text


default_secret = {
    'name': 'x',
    'secret': {
        'refresh_token': 'a-refresh-token',
    },
}
default_googlefileselect = {
    "id": "aushwyhtbndh7365YHALsdfsdf987IBHJB98uc9uisdj",
    "name": "Police Data",
    "url": "http://example.org/police-data",
    "mimeType": "application/vnd.google-apps.spreadsheet",
}


P = MockParams.factory(google_credentials=default_secret,
                       googlefileselect=default_googlefileselect,
                       has_header=True)


def fetch(**kwargs):
    params = P(**kwargs)
    return googlesheets.fetch(params)


class GoogleSheetsTests(unittest.TestCase):
    def setUp(self):
        super().setUp()

        # Set up auth
        self.requests = Mock()
        self.requests.get = Mock(
            return_value=MockResponse(404, 'Test not written')
        )
        self.oauth_service = Mock()
        self.oauth_service.requests_or_str_error = Mock(
            return_value=self.requests
        )
        self.oauth_service_lookup_patch = patch.object(
            oauth.OAuthService,
            'lookup_or_none',
            return_value=self.oauth_service
        )
        self.oauth_service_lookup_patch.start()

    def tearDown(self):
        self.oauth_service_lookup_patch.stop()

        super().tearDown()

    def test_render_no_file(self):
        fetch_result = fetch(googlefileselect='')
        self.assertEqual(fetch_result.error, '')
        self.assertTrue(fetch_result.dataframe.empty)

    def _assert_happy_path(self, fetch_result):
        self.requests.get.assert_called_with(
            'https://www.googleapis.com/drive/v3/files/'
            'aushwyhtbndh7365YHALsdfsdf987IBHJB98uc9uisdj?alt=media'
        )

        self.assertEqual(fetch_result.error, '')
        assert_frame_equal(fetch_result.dataframe, expected_table)

    def test_fetch_csv(self):
        self.requests.get.return_value = MockResponse(200, example_csv)
        fetch_result = fetch(googlefileselect={**default_googlefileselect,
                                               'mimeType': 'text/csv'})
        self._assert_happy_path(fetch_result)

    def test_fetch_tsv(self):
        self.requests.get.return_value = MockResponse(200, example_tsv)
        fetch_result = fetch(googlefileselect={
            **default_googlefileselect,
            'mimeType': 'text/tab-separated-values',
        })
        self._assert_happy_path(fetch_result)

    def test_fetch_xls(self):
        self.requests.get.return_value = MockResponse(200, example_xls)
        fetch_result = fetch(googlefileselect={
            **default_googlefileselect,
            'mimeType': 'application/vnd.ms-excel',
        })
        self._assert_happy_path(fetch_result)

    def test_fetch_xlsx(self):
        self.requests.get.return_value = MockResponse(200, example_xlsx)
        fetch_result = fetch(googlefileselect={
            **default_googlefileselect,
            'mimeType':
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })
        self._assert_happy_path(fetch_result)

    def test_no_first_row_header(self):
        self.requests.get.return_value = MockResponse(200, example_csv)
        kwargs = {
            'googlefileselect': {
                **default_googlefileselect,
                'mimeType': 'text/csv',
            },
            'has_header': False,
        }
        fetch_result = fetch(**kwargs)
        result = googlesheets.render(pd.DataFrame(), P(**kwargs),
                                     fetch_result=fetch_result)
        assert_frame_equal(result, pd.DataFrame({
            '0': ['foo', '1', '2'],
            '1': ['bar', '2', '3'],
        }))

    def test_no_table_on_missing_auth(self):
        fetch_result = fetch(google_credentials=None)
        self.assertTrue(fetch_result.dataframe.empty)
        self.assertEqual(fetch_result.error,
                         'Not authorized. Please connect to Google Drive.')

    def test_no_table_on_http_error(self):
        self.requests.get.side_effect = \
            requests.exceptions.ReadTimeout('read timeout')
        fetch_result = fetch()
        self.assertTrue(fetch_result.dataframe.empty)
        self.assertEqual(fetch_result.error, 'read timeout')

    def test_no_table_on_missing_table(self):
        self.requests.get.return_value = MockResponse(404, 'not found')
        fetch_result = fetch()
        self.assertTrue(fetch_result.dataframe.empty)
        self.assertEqual(fetch_result.error,
                         'HTTP 404 from Google: not found')

    def test_render(self):
        self.requests.get.return_value = MockResponse(200, example_csv)
        kwargs = {
            'googlefileselect': {
                **default_googlefileselect,
                'mimeType': 'text/csv',
            }
        }
        fetch_result = fetch(**kwargs)
        result = googlesheets.render(pd.DataFrame(), P(**kwargs),
                                     fetch_result=fetch_result)
        assert_frame_equal(result, expected_table)

    def test_render_missing_fetch_result_returns_empty(self):
        kwargs = {
            'googlefileselect': {
                **default_googlefileselect,
                'mimeType': 'text/csv',
            }
        }
        result = googlesheets.render(pd.DataFrame(), P(), fetch_result=None)
        assert_frame_equal(result, pd.DataFrame())
