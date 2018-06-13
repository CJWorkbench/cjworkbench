from django.conf import settings
from server.tests.utils import LoggedInTestCase, load_and_add_module, get_param_by_id_name
from server.modules.googlesheets import GoogleSheets
from unittest.mock import patch, Mock
from server.sanitizedataframe import sanitize_dataframe
from server import oauth
import requests.exceptions
import pandas as pd
import os.path
import io
import json


example_csv = 'foo,bar\n1,2\n2,3'


class MockResponse:
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text
        self.content = text.encode('utf-8')


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
            'secret': { 'refresh_token': 'a-refresh-token' },
        })
        self.credentials_param.save()
        self.file_param = get_param_by_id_name('googlefileselect')
        self.file_param.value = json.dumps({
            "id": "aushwyhtbndh7365YHALsdfsdf987IBHJB98uc9uisdj",
            "name": "Police Data",
            "url": "http://example.org/police-data",
            "type": "document",
            "mimeType": "application/vnd.google-apps.spreadsheet",
        })
        self.file_param.save()

        # our test data
        self.test_table = pd.read_csv(io.StringIO(example_csv))
        sanitize_dataframe(self.test_table)


    def tearDown(self):
        self.oauth_service_lookup_patch.stop()

        super().tearDown()


    def test_render_no_file(self):
        self.assertIsNone(GoogleSheets.render(self.wf_module, None))


    def test_event_fetch_google_sheet(self):
        self.requests.get.return_value = MockResponse(200, example_csv)

        GoogleSheets.event(self.wf_module)

        self.requests.get.assert_called_with(
            'https://www.googleapis.com/drive/v3/files/aushwyhtbndh7365YHALsdfsdf987IBHJB98uc9uisdj/export?mimeType=text%2Fcsv'
        )

        # Check that the data was actually stored
        self.assertEqual(self.wf_module.error_msg, '')
        self.assertTrue(self.wf_module.retrieve_fetched_table().equals(self.test_table))


    def test_event_fetch_csv(self):
        self.file_param.value = json.dumps({
            "id": "aushwyhtbndh7365YHALsdfsdf987IBHJB98uc9uisdj",
            "name": "Police Data",
            "url": "http://example.org/police-data",
            "type": "file",
            "mimeType": "text/csv",
        })
        self.file_param.save()
        self.requests.get.return_value = MockResponse(200, example_csv)

        GoogleSheets.event(self.wf_module)

        self.requests.get.assert_called_with(
            'https://www.googleapis.com/drive/v3/files/aushwyhtbndh7365YHALsdfsdf987IBHJB98uc9uisdj?alt=media'
        )

        self.assertEqual(self.wf_module.error_msg, '')
        self.assertTrue(self.wf_module.retrieve_fetched_table().equals(self.test_table))


    def test_empty_table_on_missing_auth(self):
        self.credentials_param.value = ''
        self.credentials_param.save()

        GoogleSheets.event(self.wf_module)

        self.assertEqual(len(self.wf_module.retrieve_fetched_table()), 0)
        self.assertEqual(self.wf_module.error_msg,
                         'Not authorized. Please connect to Google Drive.')


    def test_empty_table_on_http_error(self):
        self.requests.get.side_effect = requests.exceptions.ReadTimeout('read timeout')
        GoogleSheets.event(self.wf_module)

        self.assertEqual(len(self.wf_module.retrieve_fetched_table()), 0)
        self.assertEqual(self.wf_module.error_msg, 'read timeout')


    def test_empty_table_on_missing_table(self):
        self.requests.get.return_value = MockResponse(404, 'not found')
        GoogleSheets.event(self.wf_module)

        self.assertEqual(len(self.wf_module.retrieve_fetched_table()), 0)
        self.assertEqual(
            self.wf_module.error_msg,
            'HTTP 404 from Google: not found'
        )


    def test_render(self):
        stored_datetime = self.wf_module.store_fetched_table(self.test_table)
        self.wf_module.set_fetched_data_version(stored_datetime)
        self.wf_module.save()
        render = GoogleSheets.render(self.wf_module, None)
        self.assertTrue(render.equals(self.test_table))
