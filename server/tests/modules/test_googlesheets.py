from server.tests.utils import *
from django.test import override_settings, RequestFactory
from server.modules.googlesheets import *
from django.http import HttpResponseBadRequest
from unittest.mock import patch
from apiclient.http import HttpMock

gdrive_files = open( os.path.join(settings.BASE_DIR, 'server/tests/test_data/google_drive_files.json') ).read()

gdrive_file = open( os.path.join(settings.BASE_DIR, 'server/tests/test_data/google_drive_file.json') ).read()

class GoogleSheetsTests(LoggedInTestCase):

    def setUp(self):
        super(GoogleSheetsTests, self).setUp()
        googlesheets_def = load_module_def('googlesheets')
        self.wf_module = load_and_add_module(None, googlesheets_def)
        param_id = get_param_by_id_name('fileselect').pk
        factory = RequestFactory()
        request_event = factory.get('/api/parameters/%d/event' % param_id)
        request_event.user = self.user
        request_event.session = self.client.session
        self.request_event = request_event

    def test_render_no_file(self):
        self.assertIsNone(GoogleSheets.render(self.wf_module))

    @patch
    def test_event_fetch_files(self):
        self.assertEqual(GoogleSheets.event(self.wf_module, event={'type':'fetchFiles'}, request=self.request_event), False)

    def test_event_fetch_file(self):
        self.assertEqual(GoogleSheets.event(self.wf_module, event={'type':'fetchFile'}, request=self.request_event), False)

    def test_event_click(self):
        self.assertEqual(GoogleSheets.event(self.wf_module, event={'type':'click'}, request=self.request_event), False)
