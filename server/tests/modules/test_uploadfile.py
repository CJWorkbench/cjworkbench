from server.modules.uploadfile import *
from server.tests.utils import *
import pandas as pd
import tempfile
from django.test import override_settings

# This does not test the upload and parsing path, specifically UploadedFile.upload_to_table
# See UploadFileViewTests for that

@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class UploadFileTests(LoggedInTestCase):
    def setUp(self):
        super(UploadFileTests, self).setUp()  # log in
        self.wfm = load_and_add_module('uploadfile')

        self.csv_table = pd.read_csv(mock_csv_path)


    def test_first_applied(self):
        # no upload state
        table = UploadFile.render(self.wfm, None)
        self.assertEqual(self.wfm.status, WfModule.READY)
        self.assertIsNone(table)


    def test_duplicate_module(self):
        version = self.wfm.store_fetched_table(self.csv_table)
        self.wfm.set_fetched_data_version(version)
        self.assertEqual(len(self.wfm.list_fetched_data_versions()), 1)

        wfm2 = self.wfm.duplicate(add_new_workflow('workflow 2'))
        wfm2.refresh_from_db()

        table = UploadFile.render(wfm2, None)

        self.assertEqual(len(self.wfm.list_fetched_data_versions()), 1)
        self.assertEqual(len(wfm2.list_fetched_data_versions()), 1)
        self.assertEqual(wfm2.status, WfModule.READY)
        self.assertTrue(table.equals(self.csv_table))
