import asyncio
from collections import namedtuple
import json
from unittest.mock import patch
from django.conf import settings
from rest_framework import status
from rest_framework.test import force_authenticate, APIRequestFactory
from server import minio
from server.models import ModuleVersion, User, Workflow
from server.views import uploads
from server.tests.utils import LoggedInTestCase


FakeMinioStat = namedtuple('FakeMinioStat', ['size'])


future_none = asyncio.Future()
future_none.set_result(None)


class FakeSession:
    def __init__(self):
        self.session_key = None


@patch('server.rabbitmq.queue_render', future_none)
@patch('server.models.Delta.ws_notify', future_none)
class UploadFileViewTests(LoggedInTestCase):
    def setUp(self):
        super(UploadFileViewTests, self).setUp()  # log in
        self.workflow = Workflow.create_and_init(owner=self.user)
        with open(settings.BASE_DIR + '/server/modules/uploadfile.json') as f:
            upload_spec = json.load(f)
            module_version = ModuleVersion.create_or_replace_from_spec(
                upload_spec, source_version_hash='1.0'
            )
        self.wfm = self.workflow.tabs.first().wf_modules.create(
            order=0,
            module_id_name=module_version.id_name
        )
        self.factory = APIRequestFactory()

    def _augment_request(self, request, user):
        force_authenticate(request, user)
        request.session = FakeSession()

    @patch('server.minio.stat')
    @patch('server.rabbitmq.queue_handle_upload_DELETEME')
    def test_successful_upload(self, queue_handle_upload, stat):
        queue_handle_upload.return_value = future_none
        stat.return_value = minio.Stat(10)

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

    @patch('server.minio.remove')
    def test_post_with_non_owner_gives_403(self, remove):
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
        remove.assert_called_with(
            'our-bucket',
            'eb785452-f0f2-4ebe-97ce-e225e346148e.xlsx'
        )
