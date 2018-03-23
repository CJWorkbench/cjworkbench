from server.modules.uploadfile import *
from server.models import StoredObject,UploadedFile
from server.tests.utils import *
import requests_mock
import pandas as pd
import os
import tempfile
from django.test import override_settings
from django.core.files.storage import default_storage

mock_csv_path = os.path.join(settings.BASE_DIR, 'server/tests/test_data/sfpd.csv')
mock_xslx_path = os.path.join(settings.BASE_DIR, 'server/tests/test_data/test.xlsx')

@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class UploadFileTests(LoggedInTestCase):
    def setUp(self):
        super(UploadFileTests, self).setUp()  # log in
        self.wfm = load_and_add_module('uploadfile')

        self.csv_table = pd.read_csv(mock_csv_path)
        self.xlsx_table = pd.read_excel(mock_xslx_path)

    # create an UploadedFile like our form does
    def create_uploaded_file(self, path):
        fname = os.path.basename(path)
        file = default_storage.save(fname, open(path, 'rb'))
        uf = UploadedFile.objects.create(
            wf_module=self.wfm,
            name=fname,
            size=os.stat(path).st_size,
            uuid='XXXXUUID',
            file=file)
        return uf

    def test_csv_parse(self):
        self.assertEqual(len(self.wfm.list_fetched_data_versions()), 0)
        uf = self.create_uploaded_file(mock_csv_path)

        upload_to_table(self.wfm, uf)

        # should have turned UploadedFile into a table and stored it
        self.assertEqual(len(self.wfm.list_fetched_data_versions()), 1)
        self.assertTrue(self.wfm.retrieve_fetched_table().equals(self.csv_table))
        self.assertEqual(UploadedFile.objects.count(), 0)


    def test_xlsx_render(self):
        self.assertEqual(len(self.wfm.list_fetched_data_versions()), 0)
        uf = self.create_uploaded_file(mock_xslx_path)

        upload_to_table(self.wfm, uf)

        # should have turned UploadedFile into a table and stored it
        self.assertEqual(len(self.wfm.list_fetched_data_versions()), 1)
        self.assertTrue(self.wfm.retrieve_fetched_table().equals(self.xlsx_table))
        self.assertEqual(UploadedFile.objects.count(), 0)


    def test_first_applied(self):
        # no upload state
        table = UploadFile.render(self.wfm, None)
        self.assertEqual(self.wfm.status, WfModule.READY)
        self.assertIsNone(table)

    def test_duplicate_module(self):
        uf = self.create_uploaded_file(mock_csv_path)
        upload_to_table(self.wfm, uf) # UploadedFile to StoredObject
        self.assertEqual(len(self.wfm.list_fetched_data_versions()), 1)

        wfm2 = self.wfm.duplicate(add_new_workflow('workflow 2'))
        wfm2.refresh_from_db()

        table = UploadFile.render(wfm2, None)

        self.assertEqual(len(self.wfm.list_fetched_data_versions()), 1)
        self.assertEqual(len(wfm2.list_fetched_data_versions()), 1)
        self.assertEqual(wfm2.status, WfModule.READY)
        self.assertTrue(table.equals(self.csv_table))
