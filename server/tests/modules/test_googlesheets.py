import os.path
import io
import json
from unittest.mock import patch, Mock
from asgiref.sync import async_to_sync
import requests.exceptions
import pandas as pd
from pandas.testing import assert_frame_equal
from server.sanitizedataframe import sanitize_dataframe
from server import oauth
from server.modules.googlesheets import GoogleSheets
from server.modules.types import ProcessResult
from server.tests.utils import LoggedInTestCase, load_and_add_module, \
        get_param_by_id_name

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


default_secret = {'refresh_token': 'a-refresh-token'}
default_googlefileselect = {
    "id": "aushwyhtbndh7365YHALsdfsdf987IBHJB98uc9uisdj",
    "name": "Police Data",
    "url": "http://example.org/police-data",
    "mimeType": "application/vnd.google-apps.spreadsheet",
}


class MockWfModule:
    def __init__(self, google_secret=default_secret,
                 googlefileselect=default_googlefileselect,
                 has_header=True):
        self.google_secret = google_secret
        self.googlefileselect = googlefileselect
        self.has_header = has_header
        self.fetched_table = None
        self.fetch_error = ''

    def get_param_checkbox(self, _):
        return self.has_header

    def get_param_raw(self, _, __):
        if not self.googlefileselect:
            return None
        else:
            return json.dumps(self.googlefileselect)

    def get_param_secret_secret(self, _):
        return self.google_secret

    def retrieve_fetched_table(self):
        return self.fetched_table


async def _commit(wf_module, result, *args, **kwargs):
    wf_module.fetched_table = result.dataframe
    wf_module.fetch_error = result.error


def fetch(*args, **kwargs):
    wf_module = MockWfModule(*args, **kwargs)

    with patch('server.modules.moduleimpl.ModuleImpl.commit_result', _commit):
        async_to_sync(GoogleSheets.event)(wf_module)

    return wf_module


class GoogleSheetsTests(LoggedInTestCase):
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
        wf_module = fetch(googlefileselect='')
        self.assertEqual(wf_module.fetch_error, '')
        self.assertTrue(wf_module.fetched_table.empty)

    def _assert_happy_path(self, wf_module):
        self.requests.get.assert_called_with(
            'https://www.googleapis.com/drive/v3/files/aushwyhtbndh7365YHALsdfsdf987IBHJB98uc9uisdj?alt=media'
        )

        self.assertEqual(wf_module.fetch_error, '')
        assert_frame_equal(wf_module.fetched_table, expected_table)

    def test_event_fetch_csv(self):
        self.requests.get.return_value = MockResponse(200, example_csv)
        wf_module = fetch(googlefileselect={**default_googlefileselect,
                                            'mimeType': 'text/csv'})
        self._assert_happy_path(wf_module)

    def test_event_fetch_tsv(self):
        self.requests.get.return_value = MockResponse(200, example_tsv)
        wf_module = fetch(googlefileselect={
            **default_googlefileselect,
            'mimeType': 'text/tab-separated-values',
        })
        self._assert_happy_path(wf_module)

    def test_event_fetch_xls(self):
        self.requests.get.return_value = MockResponse(200, example_xls)
        wf_module = fetch(googlefileselect={
            **default_googlefileselect,
            'mimeType': 'application/vnd.ms-excel',
        })
        self._assert_happy_path(wf_module)

    def test_event_fetch_xlsx(self):
        self.requests.get.return_value = MockResponse(200, example_xlsx)
        wf_module = fetch(googlefileselect={
            **default_googlefileselect,
            'mimeType':
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })
        self._assert_happy_path(wf_module)

    def test_no_first_row_header(self):
        self.requests.get.return_value = MockResponse(200, example_csv)
        wf_module = fetch(googlefileselect={**default_googlefileselect,
                                            'mimeType': 'text/csv'},
                          has_header=False)
        result = GoogleSheets.render(wf_module, pd.DataFrame())
        result.sanitize_in_place()  # TODO fix header-shift code; nix this
        assert_frame_equal(result.dataframe, pd.DataFrame({
            '0': ['foo', '1', '2'],
            '1': ['bar', '2', '3'],
        }))

    def test_no_table_on_missing_auth(self):
        wf_module = fetch(google_secret=None)
        self.assertTrue(wf_module.fetched_table.empty)
        self.assertEqual(wf_module.fetch_error,
                         'Not authorized. Please connect to Google Drive.')

    def test_no_table_on_http_error(self):
        self.requests.get.side_effect = \
            requests.exceptions.ReadTimeout('read timeout')
        wf_module = fetch()
        self.assertTrue(wf_module.fetched_table.empty)
        self.assertEqual(wf_module.fetch_error, 'read timeout')

    def test_no_table_on_missing_table(self):
        self.requests.get.return_value = MockResponse(404, 'not found')
        wf_module = fetch()
        self.assertTrue(wf_module.fetched_table.empty)
        self.assertEqual(wf_module.fetch_error,
                         'HTTP 404 from Google: not found')

    def test_render(self):
        self.requests.get.return_value = MockResponse(200, example_csv)
        wf_module = fetch(googlefileselect={**default_googlefileselect,
                                            'mimeType': 'text/csv'})
        result = GoogleSheets.render(wf_module, pd.DataFrame())
        self.assertEqual(result, ProcessResult(expected_table))
