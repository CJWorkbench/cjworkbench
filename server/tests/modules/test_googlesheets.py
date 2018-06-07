from django.conf import settings
from server.tests.utils import LoggedInTestCase, load_and_add_module, get_param_by_id_name
from server.modules.googlesheets import GoogleSheets
from unittest.mock import patch
from apiclient.http import HttpMock, HttpMockSequence
from server.sanitizedataframe import sanitize_dataframe
import pandas as pd
import os
import json

gdrive_discovery_file = os.path.join(settings.BASE_DIR, 'server/tests/test_data/google_drive_api_discovery.json')
with open(gdrive_discovery_file) as f: gdrive_discovery = f.read()

gdrive_file_meta = {
  "file": {
    "kind": "drive#file",
    "id": "aushwyhtbndh7365YHALsdfsdf987IBHJB98uc9uisdj",
    "name": "Police Data",
    "mimeType": "application/vnd.google-apps.spreadsheet"
  }
}

gdrive_file = os.path.join(settings.BASE_DIR, 'server/tests/test_data/missing_values.csv')


class HttpMocks(HttpMock):
    def __init__(self, *mocks):
        self.mocks = list(mocks)

    def request(self, *args, **kwargs):
        return self.mocks.pop(0).request(*args, **kwargs)


class DumbCredential():
    def authorize(self, the_request):
        return the_request


class GoogleSheetsTests(LoggedInTestCase):

    def setUp(self):
        super(GoogleSheetsTests, self).setUp()
        self.wf_module = load_and_add_module('googlesheets')
        self.file_param = get_param_by_id_name('fileselect')
        self.file_param.value = json.dumps(gdrive_file_meta['file'])
        self.file_param.save()

        # our test data
        self.test_table = pd.read_csv(gdrive_file)
        sanitize_dataframe(self.test_table)


    def test_render_no_file(self):
        self.assertIsNone(GoogleSheets.render(self.wf_module, None))


    @patch('cjworkbench.google_oauth.user_to_existing_oauth2_credential')
    @patch('server.modules.googlesheets.httplib2.Http')
    def test_event_fetch_file(self, httplib_patch, oauth_patch):
        oauth_patch.return_value = DumbCredential()
        auth_mock = HttpMock(filename=gdrive_discovery_file)
        data_mock = HttpMock(filename=gdrive_file)
        # Make httplib_patch return first auth_mock, then data_mock
        httplib_patch.return_value = HttpMocks(auth_mock, data_mock)

        GoogleSheets.event(self.wf_module)

        self.assertEqual(data_mock.uri, 'https://www.googleapis.com/drive/v3/files/aushwyhtbndh7365YHALsdfsdf987IBHJB98uc9uisdj/export?mimeType=text%2Fcsv')

        # Check that the data was actually stored
        self.assertTrue(self.wf_module.retrieve_fetched_table().equals(self.test_table))
        self.assertEqual(self.wf_module.error_msg, '')


    @patch('cjworkbench.google_oauth.user_to_existing_oauth2_credential')
    def test_empty_table_on_missing_auth(self, oauth_patch):
        oauth_patch.return_value = None
        GoogleSheets.event(self.wf_module)

        self.assertEqual(len(self.wf_module.retrieve_fetched_table()), 0)
        self.assertEqual(self.wf_module.error_msg,
                         'Not authorized. Please reconnect to Google Drive.')


    @patch('cjworkbench.google_oauth.user_to_existing_oauth2_credential')
    @patch('server.modules.googlesheets.httplib2.Http')
    def test_empty_table_on_missing_table(self, httplib_patch, oauth_patch):
        oauth_patch.return_value = DumbCredential()
        httplib_patch.return_value = HttpMockSequence([
            ({'status': '200'}, gdrive_discovery),
            ({'status': '404'}, 'not found'),
        ])
        GoogleSheets.event(self.wf_module)

        self.assertEqual(len(self.wf_module.retrieve_fetched_table()), 0)
        self.assertEqual(
            self.wf_module.error_msg,
            '<HttpError 404 when requesting https://www.googleapis.com/drive/v3/files/aushwyhtbndh7365YHALsdfsdf987IBHJB98uc9uisdj/export?mimeType=text%2Fcsv returned "Ok">'
        )


    def test_render(self):
        stored_datetime = self.wf_module.store_fetched_table(self.test_table)
        self.wf_module.set_fetched_data_version(stored_datetime)
        self.wf_module.save()
        render = GoogleSheets.render(self.wf_module, None)
        self.assertTrue(render.equals(self.test_table))
