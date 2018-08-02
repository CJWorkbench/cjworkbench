from server.models import UploadedFile
from server.views.UploadedFileView import UploadedFileView
from rest_framework import status
from rest_framework.test import force_authenticate, APIRequestFactory
from server.tests.utils import *
from pandas.testing import assert_frame_equal
from server.sanitizedataframe import sanitize_dataframe
from server.modules.utils import parse_bytesio
import os


class UploadFileViewTests(LoggedInTestCase):
    def setUp(self):
        super(UploadFileViewTests, self).setUp()  # log in
        self.wfm = load_and_add_module('uploadfile')
        self.factory = APIRequestFactory()

        # Path through chardet encoding detection
        with open(mock_csv_path, 'rb') as iobytes:
            self.csv_table = parse_bytesio(iobytes, 'text/csv', None).dataframe

        with open(mock_xlsx_path, 'rb') as iobytes:
            self.xlsx_table = parse_bytesio(
                iobytes,
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                None
            ).dataframe
            sanitize_dataframe(self.xlsx_table)

    def _test_successful_upload(self, path, table):
        self.assertEqual(len(self.wfm.list_fetched_data_versions()), 0)

        pathname, filename = os.path.split(path)
        put_content = {
            'wf_module' : self.wfm.id,
            'file' : open(path, 'rb'),
            'name' : filename,
            'size' : os.stat(path).st_size,
            'uuid' : 'xxxuuid'
         }

        request = self.factory.post('/api/uploadfile', put_content)
        force_authenticate(request, user=self.user)
        response = UploadedFileView.post(request=request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # should have parsed UploadedFile into a fetched table
        self.wfm.refresh_from_db()
        self.assertEqual(len(self.wfm.list_fetched_data_versions()), 1)
        assert_frame_equal(self.wfm.retrieve_fetched_table(), table)
        self.assertTrue(self.wfm.retrieve_fetched_table().equals(table))
        self.assertEqual(UploadedFile.objects.count(), 1)  # don't delete successful uploads

        # calling .get on this object must return filename and uuid
        request = self.factory.get('/api/uploadfile?wf_module=%d' % self.wfm.id)
        force_authenticate(request, user=self.user)
        response = UploadedFileView.get(request=request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        get_content = [{
            'name': put_content['name'],
            'uuid': put_content['uuid']
        }]
        self.assertEqual(json.loads(response.content.decode('utf-8')), get_content)


    def test_upload_csv(self):
        self._test_successful_upload(mock_csv_path, self.csv_table)


    def test_upload_xlsx(self):
        self._test_successful_upload(mock_xlsx_path, self.xlsx_table)


    # test when we can't parse the file, by uploading a file with an xlsx extension which is not an Excel file
    def test_bad_file(self):
        self.assertEqual(len(self.wfm.list_fetched_data_versions()), 0)

        content = {
            'wf_module': self.wfm.id,
            'file': open(mock_csv_path, 'rb'),
            'name': 'something.xlsx',
            'size': os.stat(mock_csv_path).st_size,
            'uuid': 'xxxuuid'
        }

        request = self.factory.post('/api/uploadfile', content)
        force_authenticate(request, user=self.user)
        response = UploadedFileView.post(request=request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # should set error, no new version created
        self.wfm.refresh_from_db()
        self.assertEqual(len(self.wfm.list_fetched_data_versions()), 0)
        self.assertEqual(self.wfm.status, WfModule.ERROR)
        self.assertIsNone(self.wfm.retrieve_fetched_table())
