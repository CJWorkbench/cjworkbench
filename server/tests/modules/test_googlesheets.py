from django.conf import settings
from server.tests.utils import LoggedInTestCase, load_and_add_module, get_param_by_id_name
from server.modules.googlesheets import GoogleSheets
from unittest.mock import patch
from server.sanitizedataframe import sanitize_dataframe
from collections import namedtuple
import requests.exceptions
import pandas as pd
import os.path
import json


gdrive_file = os.path.join(settings.BASE_DIR, 'server/tests/test_data/missing_values.csv')
with open(gdrive_file, encoding='utf-8') as f: gdrive_file_contents = f.read()


MockResponse = namedtuple('MockResponse', [ 'status_code', 'text' ])


class GoogleSheetsTests(LoggedInTestCase):

    def setUp(self):
        super().setUp()

        # Set up auth
        self.service_patch = patch.dict(
            settings.PARAMETER_OAUTH_SERVICES,
            { 'google_credentials': {
                'token_url': 'http://token-url',
                'refresh_url': 'http://refresh-url',
                'client_id': 'client-id',
                'client_secret': 'client-secret',
                'redirect_url': 'http://my-redirect-server',
            }}
        )
        self.service_patch.start()

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
        })
        self.file_param.save()

        # our test data
        self.test_table = pd.read_csv(gdrive_file)
        sanitize_dataframe(self.test_table)


    def tearDown(self):
        self.service_patch.stop()

        super().tearDown()


    def test_render_no_file(self):
        self.assertIsNone(GoogleSheets.render(self.wf_module, None))


    @patch('requests_oauthlib.OAuth2Session')
    def test_event_fetch_file(self, oauth_patch):
        oauth_patch.return_value.get.return_value = MockResponse(200, gdrive_file_contents)

        GoogleSheets.event(self.wf_module)

        oauth_patch.return_value.refresh_token.assert_called_once()
        oauth_patch.return_value.get.assert_called_once_with(
            'https://www.googleapis.com/drive/v3/files/aushwyhtbndh7365YHALsdfsdf987IBHJB98uc9uisdj/export?mimeType=text%2Fcsv'
        )

        # Check that the data was actually stored
        self.assertTrue(self.wf_module.retrieve_fetched_table().equals(self.test_table))
        self.assertEqual(self.wf_module.error_msg, '')


    def test_empty_table_on_missing_auth(self):
        self.credentials_param.value = ''
        self.credentials_param.save()

        GoogleSheets.event(self.wf_module)

        self.assertEqual(len(self.wf_module.retrieve_fetched_table()), 0)
        self.assertEqual(self.wf_module.error_msg,
                         'Not authorized. Please connect to Google Drive.')


    @patch('requests_oauthlib.OAuth2Session')
    def test_empty_table_on_http_error(self, oauth_patch):
        oauth_patch.return_value.get.side_effect = requests.exceptions.ReadTimeout('read timeout')
        GoogleSheets.event(self.wf_module)

        self.assertEqual(len(self.wf_module.retrieve_fetched_table()), 0)
        self.assertEqual(self.wf_module.error_msg, 'read timeout')


    @patch('requests_oauthlib.OAuth2Session')
    def test_empty_table_on_missing_table(self, oauth_patch):
        oauth_patch.return_value.get.return_value = MockResponse(404, 'not found')
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
