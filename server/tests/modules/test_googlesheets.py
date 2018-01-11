from server.tests.utils import *
from django.test import override_settings
from rest_framework.test import APIRequestFactory
from server.modules.googlesheets import *
from django.http import HttpResponseBadRequest
from unittest.mock import patch
from apiclient.http import HttpMock
from cjworkbench.google_oauth import maybe_authorize
from apiclient.http import HttpMockSequence
import pandas as pd
import io
import json
from server.views.WfModule import make_render_json

gdrive_discovery = open( os.path.join(settings.BASE_DIR, 'server/tests/test_data/google_drive_api_discovery.json') ).read()

gdrive_files = open( os.path.join(settings.BASE_DIR, 'server/tests/test_data/google_drive_files.json') ).read()

gdrive_file_meta = open( os.path.join(settings.BASE_DIR, 'server/tests/test_data/google_drive_file.json') ).read()

gdrive_file = open( os.path.join(settings.BASE_DIR, 'server/tests/test_data/police_data.csv') ).read()

def mock_http_files():
    return HttpMockSequence([
        ({'status': '200'}, gdrive_discovery),
        ({'status': '200'}, gdrive_files)])

def mock_http_file():
    return HttpMockSequence([
        ({'status': '200'}, gdrive_discovery),
        ({'status': '200'}, gdrive_file)])

class DumbCredential():
    def authorize(self, the_request):
        return the_request

class GoogleSheetsTests(LoggedInTestCase):

    def setUp(self):
        super(GoogleSheetsTests, self).setUp()
        googlesheets_def = load_module_def('googlesheets')
        self.wf_module = load_and_add_module(None, googlesheets_def)
        self.file_param = get_param_by_id_name('fileselect')

        drive_file_response = json.loads(gdrive_file_meta)
        self.file_param.value = json.dumps(drive_file_response['file'])
        self.file_param.save()

        param_id = self.file_param.pk

        factory = APIRequestFactory()

        request_event = factory.get('/api/parameters/%d/event' % param_id)
        request_event.user = self.user
        request_event.session = self.client.session
        self.request_event = request_event

        request_post = factory.post('/api/parameters/%d/event' % param_id, json.loads(gdrive_file_meta), format='json')
        request_post.user = self.user
        request_post.session = self.client.session
        self.request_post = request_post

        # To skip the oauth flow we mock maybe_authorize to return
        # an authorization and a "credential" with an authorize method
        # that just returns whatever you give it
        auth_patch = patch('server.modules.googlesheets.maybe_authorize')
        self.auth_patch = auth_patch.start()
        dumb_credential = DumbCredential()
        self.auth_patch.return_value = (True, dumb_credential)
        self.addCleanup(auth_patch.stop)

        # To mock the Google api we mock httplib2 so it returns a sequence of
        # specialized mock http objects, which are set per test depending on
        # what we're trying to return.
        httplib_patch = patch('server.modules.googlesheets.httplib2.Http')
        self.httplib_patch = httplib_patch.start()
        self.addCleanup(httplib_patch.stop)

    def test_render_no_file(self):
        self.assertIsNone(GoogleSheets.render(self.wf_module, None))

    def test_event_fetch_files(self):
        self.httplib_patch.return_value = mock_http_files()
        result = GoogleSheets.event(self.wf_module, event={'type':'fetchFiles'}, request=self.request_event)
        self.assertEqual(json.loads(result.content.decode('utf-8')), json.loads(gdrive_files))

    @patch('server.modules.googlesheets.GoogleSheets.get_spreadsheet', return_value=gdrive_file)
    def test_event_fetch_file(self, mock_get_spreadsheet):
        self.httplib_patch.return_value = mock_http_file()
        file_meta = json.loads(gdrive_file_meta)
        result = GoogleSheets.event(self.wf_module, event={'type':'fetchFile'}, request=self.request_post)

        mock_get_spreadsheet.assert_called_with( \
            self.request_post, file_meta['file']['id'], owner=self.wf_module.workflow.owner)
        self.assertEqual(result.status_code, 204)
        self.assertEqual(json.loads(result.content.decode('utf-8')), {})

    @patch('server.modules.googlesheets.GoogleSheets.get_spreadsheet', return_value=gdrive_file)
    def test_event_click(self, mock_get_spreadsheet):
        self.httplib_patch.return_value = mock_http_file()
        file_meta = json.loads(self.file_param.value)
        result = GoogleSheets.event(self.wf_module, event={'type':'click'}, request=self.request_post)

        mock_get_spreadsheet.assert_called_with( \
            self.request_post, file_meta['id'], owner=self.wf_module.workflow.owner)
        self.assertEqual(result.status_code, 204)
        self.assertEqual(json.loads(result.content.decode('utf-8')), {})

    @patch('server.modules.googlesheets.GoogleSheets.get_spreadsheet', return_value=gdrive_file)
    def test_event_no_event_type(self, mock_get_spreadsheet):
        self.httplib_patch.return_value = mock_http_file()
        file_meta = json.loads(self.file_param.value)
        result = GoogleSheets.event(self.wf_module, None, request=self.request_post)

        mock_get_spreadsheet.assert_called_with( \
            self.request_post, file_meta['id'], owner=self.wf_module.workflow.owner)
        self.assertEqual(result.status_code, 204)
        self.assertEqual(json.loads(result.content.decode('utf-8')), {})

    def test_get_file_and_render(self):
        self.httplib_patch.return_value = mock_http_file()
        file_meta = json.loads(gdrive_file_meta)
        GoogleSheets.event(self.wf_module, event={'type':'fetchFile'}, request=self.request_post)
        render = GoogleSheets.render(self.wf_module, None)
        table = pd.read_csv(io.StringIO(gdrive_file))
        self.assertTrue(render.equals(table))

    def test_get_sheets(self):
        self.httplib_patch.return_value = mock_http_files()
        result = GoogleSheets.get_spreadsheets(self.request_post, self.wf_module.workflow.owner)
        self.assertEqual(json.loads(result.content.decode('utf-8')), json.loads(gdrive_files))
