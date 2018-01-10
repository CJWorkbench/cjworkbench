from server.tests.utils import *
from django.test import override_settings
from rest_framework.test import APIRequestFactory
from server.modules.googlesheets import *
from django.http import HttpResponseBadRequest
from unittest.mock import patch
from apiclient.http import HttpMock
from cjworkbench.google_oauth import maybe_authorize
from apiclient.http import HttpMockSequence
import json

gdrive_discovery = open( os.path.join(settings.BASE_DIR, 'server/tests/test_data/google_drive_api_discovery.json') ).read()

gdrive_files = open( os.path.join(settings.BASE_DIR, 'server/tests/test_data/google_drive_files.json') ).read()

gdrive_file_meta = open( os.path.join(settings.BASE_DIR, 'server/tests/test_data/google_drive_file.json') ).read()

gdrive_file = open( os.path.join(settings.BASE_DIR, 'server/tests/test_data/police_data.csv') ).read()

mock_http_files = HttpMockSequence([
    ({'status': '200'}, gdrive_discovery),
    ({'status': '200'}, gdrive_files)])

mock_http_file = HttpMockSequence([
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
        param_id = get_param_by_id_name('fileselect').pk

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

        # To mock the Google api we mock httplib2 so it returns a specialized
        # mock http object, which returns the "api discovery" document
        httplib_patch = patch('server.modules.googlesheets.httplib2.Http')
        self.httplib_patch = httplib_patch.start()
        self.addCleanup(httplib_patch.stop)

    def test_render_no_file(self):
        self.assertIsNone(GoogleSheets.render(self.wf_module, None))

    def test_event_fetch_files(self):
        self.httplib_patch.return_value = mock_http_files
        result = GoogleSheets.event(self.wf_module, event={'type':'fetchFiles'}, request=self.request_event)
        self.assertEqual(json.loads(result.content), json.loads(gdrive_files))

    def test_event_fetch_file(self):
        self.httplib_patch.return_value = mock_http_file
        result = GoogleSheets.event(self.wf_module, event={'type':'fetchFile'}, request=self.request_post)
        self.assertEqual(json.loads(result.content), {})
