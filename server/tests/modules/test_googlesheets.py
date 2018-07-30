import os.path
import io
import json
from unittest.mock import patch, Mock
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


class MockResponse:
    def __init__(self, status_code, text):
        self.status_code = status_code

        if isinstance(text, str):
            self.text = text
            self.content = text.encode('utf-8')
        else:
            self.content = text


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

        # Create WfModule
        self.wf_module = load_and_add_module('googlesheets')
        self.credentials_param = get_param_by_id_name('google_credentials')
        self.credentials_param.value = json.dumps({
            'name': 'file',
            'secret': {'refresh_token': 'a-refresh-token'},
        })
        self.credentials_param.save()
        self.file_param = get_param_by_id_name('googlefileselect')
        self.file_param.value = json.dumps({
            "id": "aushwyhtbndh7365YHALsdfsdf987IBHJB98uc9uisdj",
            "name": "Police Data",
            "url": "http://example.org/police-data",
            "mimeType": "application/vnd.google-apps.spreadsheet",
        })
        self.file_param.save()

        # our test data
        self.test_table = pd.read_csv(
            io.BytesIO(example_csv),
            encoding='utf-8'
        )
        sanitize_dataframe(self.test_table)

    def _set_file_type(self, mime_type):
        data = json.loads(self.file_param.value)
        data['mimeType'] = mime_type
        self.file_param.value = json.dumps(data)
        self.file_param.save()

    def tearDown(self):
        self.oauth_service_lookup_patch.stop()

        super().tearDown()

    def test_render_no_file(self):
        result = GoogleSheets.render(self.wf_module, None)
        self.assertEqual(result, ProcessResult(pd.DataFrame()))

    def _assert_file_event_happy_path(self):
        GoogleSheets.event(self.wf_module)

        self.requests.get.assert_called_with(
            'https://www.googleapis.com/drive/v3/files/aushwyhtbndh7365YHALsdfsdf987IBHJB98uc9uisdj?alt=media'
        )

        self.assertEqual(self.wf_module.error_msg, '')
        assert_frame_equal(self.wf_module.retrieve_fetched_table().astype(str),
                           self.test_table.astype(str))

    def test_event_fetch_csv(self):
        self._set_file_type('text/csv')
        self.requests.get.return_value = MockResponse(200, example_csv)
        self._assert_file_event_happy_path()

    def test_event_fetch_tsv(self):
        self._set_file_type('text/tab-separated-values')
        self.requests.get.return_value = MockResponse(200, example_tsv)
        self._assert_file_event_happy_path()

    def test_event_fetch_xls(self):
        self._set_file_type('application/vnd.ms-excel')
        self.requests.get.return_value = MockResponse(200, example_xls)
        self._assert_file_event_happy_path()

    def test_event_fetch_xlsx(self):
        self._set_file_type(
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        self.requests.get.return_value = MockResponse(200, example_xlsx)
        self._assert_file_event_happy_path()

    def test_no_table_on_missing_auth(self):
        self.credentials_param.value = ''
        self.credentials_param.save()

        GoogleSheets.event(self.wf_module)

        self.assertIsNone(self.wf_module.retrieve_fetched_table())
        self.assertEqual(self.wf_module.error_msg,
                         'Not authorized. Please connect to Google Drive.')

    def test_no_table_on_http_error(self):
        self.requests.get.side_effect = requests.exceptions.ReadTimeout('read timeout')
        GoogleSheets.event(self.wf_module)

        self.assertIsNone(self.wf_module.retrieve_fetched_table())
        self.assertEqual(self.wf_module.error_msg, 'read timeout')

    def test_no_table_on_missing_table(self):
        self.requests.get.return_value = MockResponse(404, 'not found')
        GoogleSheets.event(self.wf_module)

        self.assertIsNone(self.wf_module.retrieve_fetched_table())
        self.assertEqual(
            self.wf_module.error_msg,
            'HTTP 404 from Google: not found'
        )

    def test_render(self):
        stored_datetime = self.wf_module.store_fetched_table(self.test_table)
        self.wf_module.set_fetched_data_version(stored_datetime)
        self.wf_module.save()
        result = GoogleSheets.render(self.wf_module, None)
        self.assertEqual(result, ProcessResult(self.test_table))
