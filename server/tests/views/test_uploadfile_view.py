import asyncio
from collections import namedtuple
import json
import io
from unittest.mock import patch
import pandas as pd
from pandas.testing import assert_frame_equal
from rest_framework import status
from rest_framework.test import force_authenticate, APIRequestFactory
from server import rabbitmq
from server.models import UploadedFile, User
from server.views.UploadedFileView import get_uploadedfile
from server.views import uploads
from server.tests.utils import load_and_add_module, LoggedInTestCase


FakeMinioStat = namedtuple('FakeMinioStat', ['size'])


future_none = asyncio.Future()
future_none.set_result(None)


class FakeSession:
    def __init__(self):
        self.session_key = None


@patch('server.models.Delta.schedule_execute', future_none)
@patch('server.models.Delta.ws_notify', future_none)
class UploadFileViewTests(LoggedInTestCase):
    def setUp(self):
        super(UploadFileViewTests, self).setUp()  # log in
        self.wfm = load_and_add_module('uploadfile')
        self.factory = APIRequestFactory()

    def _augment_request(self, request, user):
        force_authenticate(request, user)
        request.session = FakeSession()

    @patch('minio.api.Minio.stat_object')
    @patch('server.rabbitmq.queue_handle_upload_DELETEME')
    def test_successful_upload(self, queue_handle_upload, stat_object):
        queue_handle_upload.return_value = future_none
        stat_object.return_value = FakeMinioStat(10)

        uuid = 'eb785452-f0f2-4ebe-97ce-e225e346148e',
        filename = 'test.csv',
        ext = 'csv',
        size = 10

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

        uploaded_file = self.wfm.uploaded_files.first()

        queue_handle_upload.assert_called_with(uploaded_file)

        # pending: https://www.pivotaltracker.com/story/show/161509317
        # # calling .get on this object must return filename and uuid
        # request = self.factory.get(f'/api/uploadfile/{self.wfm.id}')
        # self._augment_request(request, self.user)
        # response = get_uploadedfile(request, self.wfm.id)
        # self.assertEqual(response.status_code, status.HTTP_200_OK)
        #
        # self.assertEqual(json.loads(response.content.decode('utf-8')), [{
        #     'name': filename,
        #     'uuid': uuid,
        #     's3Key': f'{uuid}.{ext}',
        #     's3Bucket': 'our-bucket',
        #     'size': size,
        # }])

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
