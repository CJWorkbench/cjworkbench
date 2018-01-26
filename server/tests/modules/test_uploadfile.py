from server.modules.uploadfile import *
from server.models.StoredObject import *
from server.tests.utils import *
import requests_mock
import pandas as pd
import os
import tempfile
from django.test import override_settings
from django.core.files.storage import default_storage

mock_csv_path = os.path.join(settings.BASE_DIR, 'server/tests/test_data/sfpd.csv')
mock_xslx_path = os.path.join(settings.BASE_DIR, 'server/tests/modules/test.xlsx')

@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class UploadFileTests(LoggedInTestCase):
    def setUp(self):
        super(UploadFileTests, self).setUp()  # log in
        self.wfm = load_and_add_module('uploadfile')

        self.csv_table = pd.read_csv(mock_csv_path)
        self.xlsx_table = pd.read_excel(mock_xslx_path)

    # create StoredObject equivalent to file upload
    def create_uploaded_file(self, path):
        fname = os.path.basename(path)
        file = default_storage.save(fname, open(path, 'rb'))
        so = StoredObject.objects.create(
            wf_module=self.wfm,
            type=StoredObject.UPLOADED_FILE,
            stored_at = timezone.now(),
            metadata='whee metadata',
            name=fname,
            size=os.stat(path).st_size,
            uuid='XXXXUUID',
            file=file)
        self.wfm.set_fetched_data_version(so.stored_at)
        return so


    def test_csv_render(self):
        so = self.create_uploaded_file(mock_csv_path)
        self.assertEqual(len(self.wfm.list_fetched_data_versions()), 1)

        table = UploadFile.render(self.wfm, None)

        self.assertEqual(self.wfm.status, WfModule.READY)
        self.assertTrue(table.equals(self.csv_table))


    def test_xlsx_render(self):
        so = self.create_uploaded_file(mock_xslx_path)
        self.assertEqual(len(self.wfm.list_fetched_data_versions()), 1)

        table = UploadFile.render(self.wfm, None)

        self.assertEqual(self.wfm.status, WfModule.READY)
        self.assertTrue(table.equals(self.xlsx_table))


    def test_duplicate_module(self):
        so = self.create_uploaded_file(mock_csv_path)
        self.assertEqual(len(self.wfm.list_fetched_data_versions()), 1)

        wfm2 = self.wfm.duplicate(add_new_workflow('workflow 2'))
        wfm2.refresh_from_db()

        table = UploadFile.render(wfm2, None)

        self.assertEqual(wfm2.status, WfModule.READY)
        self.assertTrue(table.equals(self.csv_table))
