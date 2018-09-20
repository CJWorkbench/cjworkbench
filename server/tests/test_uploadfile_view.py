from collections import namedtuple
from contextlib import contextmanager
import json
import io
from unittest.mock import patch
import pandas as pd
from pandas.testing import assert_frame_equal
from rest_framework import status
from rest_framework.test import force_authenticate, APIRequestFactory
from server.models import UploadedFile, User
from server.views.UploadedFileView import get_uploadedfile
from server.views import uploads
from server.tests.utils import load_and_add_module, LoggedInTestCase, \
        mock_xlsx_path


FakeMinioStat = namedtuple('FakeMinioStat', ['size'])


class FakeMinioObject(io.BytesIO):
    def release_conn(self):
        pass


class FakeSession:
    def __init__(self):
        self.session_key = None


@contextmanager
def mock_file(b):
    with io.BytesIO(b) as bio:
        yield bio


Csv = """A,B
1,fôo
2,bar""".encode('utf-8')


XlsxType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


class UploadFileViewTests(LoggedInTestCase):
    def setUp(self):
        super(UploadFileViewTests, self).setUp()  # log in
        self.wfm = load_and_add_module('uploadfile')
        self.factory = APIRequestFactory()

    def _augment_request(self, request, user):
        force_authenticate(request, user)
        request.session = FakeSession()

    def _test_successful_upload(self, *, uuid, filename, ext, size,
                                expected_table):
        self.assertEqual(len(self.wfm.list_fetched_data_versions()), 0)

        request_content = {
            'wf_module': self.wfm.id,
            'success': True,
            'uuid': uuid,
            'bucket': 'our-bucket',
            'key': f'{uuid}.{ext}',
            'name': filename,
            'size': size,
        }

        request = self.factory.post('/api/uploadfile/', request_content)
        self._augment_request(request, self.user)
        response = uploads.handle_s3(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # should have parsed UploadedFile into a fetched table
        self.wfm.refresh_from_db()
        self.assertEqual(len(self.wfm.list_fetched_data_versions()), 1)
        assert_frame_equal(self.wfm.retrieve_fetched_table(), expected_table)
        # don't delete successful uploads
        self.assertEqual(UploadedFile.objects.count(), 1)

        # calling .get on this object must return filename and uuid
        request = self.factory.get(f'/api/uploadfile/{self.wfm.id}')
        self._augment_request(request, self.user)
        response = get_uploadedfile(request, self.wfm.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(json.loads(response.content.decode('utf-8')), [{
            'name': filename,
            'uuid': uuid,
            's3Key': f'{uuid}.{ext}',
            's3Bucket': 'our-bucket',
            'size': size,
        }])

    @patch('minio.api.Minio.get_object')
    @patch('minio.api.Minio.stat_object')
    def test_upload_csv(self, stat, s3_open):
        # Path through chardet encoding detection
        s3_open.return_value = FakeMinioObject(Csv)
        stat.return_value = FakeMinioStat(len(Csv))

        csv_table = pd.DataFrame({'A': [1, 2], 'B': ['fôo', 'bar']})
        csv_table['B'] = csv_table['B'].astype('category')

        self._test_successful_upload(
            uuid='eb785452-f0f2-4ebe-97ce-e225e346148e',
            filename='test.csv',
            ext='csv',
            size=len(Csv),
            expected_table=csv_table
        )
        s3_open.assert_called_with(
            'our-bucket',
            'eb785452-f0f2-4ebe-97ce-e225e346148e.csv'
        )

    @patch('minio.api.Minio.get_object')
    @patch('minio.api.Minio.stat_object')
    def test_upload_xlsx(self, stat, s3_open):
        with open(mock_xlsx_path, 'rb') as bio:
            b = bio.read()
        s3_open.return_value = FakeMinioObject(b)
        stat.return_value = FakeMinioStat(len(b))

        expected_table = pd.DataFrame({
            'Month': ['Jan', 'Feb'],
            'Amount': [10, 20]
        })

        self._test_successful_upload(
            uuid='eb785452-f0f2-4ebe-97ce-e225e346148e',
            filename='test.xlsx',
            ext='xlsx',
            size=len(b),
            expected_table=expected_table
        )
        s3_open.assert_called_with(
            'our-bucket',
            'eb785452-f0f2-4ebe-97ce-e225e346148e.xlsx'
        )

    @patch('minio.api.Minio.get_object')
    @patch('minio.api.Minio.stat_object')
    @patch('minio.api.Minio.remove_object')
    def test_invalid_xlsx_gives_error(self, remove_object, stat_object,
                                      get_object):
        get_object.return_value = FakeMinioObject(b'not an xlsx')
        stat_object.return_value = FakeMinioStat(10)

        request_content = {
            'wf_module': self.wfm.id,
            'success': True,
            'uuid': 'eb785452-f0f2-4ebe-97ce-e225e346148e',
            'bucket': 'our-bucket',
            'key': 'eb785452-f0f2-4ebe-97ce-e225e346148e.xlsx',
            'name': 'invalid.xlsx',
            'size': 10,
        }

        request = self.factory.post('/api/uploadfile/', request_content)
        self._augment_request(request, self.user)
        response = uploads.handle_s3(request=request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        remove_object.assert_called_with(
            'our-bucket',
            'eb785452-f0f2-4ebe-97ce-e225e346148e.xlsx'
        )

        # should set error, no new version created
        self.wfm.refresh_from_db()
        self.assertEqual(len(self.wfm.list_fetched_data_versions()), 0)
        self.assertIsNone(self.wfm.retrieve_fetched_table())
        self.assertEqual(
            self.wfm.fetch_error,
            'Error reading Excel file: Unsupported format, or corrupt file: '
            "Expected BOF record; found b'not an x'"
        )

    @patch('minio.api.Minio.get_object')
    @patch('minio.api.Minio.remove_object')
    def test_post_with_non_owner_gives_403(self, remove_object, get_object):
        request_content = {
            'wf_module': self.wfm.id,
            'success': True,
            'uuid': 'eb785452-f0f2-4ebe-97ce-e225e346148e',
            'bucket': 'our-bucket',
            'key': 'eb785452-f0f2-4ebe-97ce-e225e346148e.xlsx',
            'name': 'wont-be-opened.xlsx',
            'size': 10,
        }

        wrong_user = User.objects.create(username='no', email='no@example.org',
                                         password='password')

        request = self.factory.post('/api/uploadfile/', request_content)
        self._augment_request(request, wrong_user)
        response = uploads.handle_s3(request=request)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Ensure no data leaks about the file contents
        get_object.assert_not_called()
        remove_object.assert_called_with(
            'our-bucket',
            'eb785452-f0f2-4ebe-97ce-e225e346148e.xlsx'
        )
