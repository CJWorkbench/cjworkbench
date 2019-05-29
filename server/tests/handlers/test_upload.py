from base64 import b64encode
import hashlib
from unittest.mock import patch
import uuid as uuidgen
from django.contrib.auth.models import User
from django.utils import timezone
import urllib3
from server.handlers.upload import create_multipart_upload, \
        abort_multipart_upload, presign_upload_part, prepare_upload, \
        complete_upload, complete_multipart_upload
from server.models import Workflow, UploadedFile
from server import minio
from .util import HandlerTestCase


def _base64_md5sum(b: bytes) -> str:
    h = hashlib.md5()
    h.update(b)
    md5sum = h.digest()
    return b64encode(md5sum).decode('ascii')


async def async_noop(*args, **kwargs):
    pass


class UploadTest(HandlerTestCase):
    def test_prepare_upload_happy_path(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.create_and_init(owner=user)
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            module_id_name='x',
        )

        data = b'1234567'
        md5sum = _base64_md5sum(data)
        response = self.run_handler(prepare_upload, user=user,
                                    workflow=workflow, wfModuleId=wf_module.id,
                                    filename='abc.csv', nBytes=len(data),
                                    base64Md5sum=md5sum)
        self.assertEqual(response.error, '')
        wf_module.refresh_from_db()
        self.assertIsNone(wf_module.inprogress_file_upload_id)
        self.assertTrue(
            response.data['key'].startswith(wf_module.uploaded_file_prefix)
        )
        self.assertTrue(response.data['key'] in response.data['url'])
        http = urllib3.PoolManager()
        response = http.request('PUT', response.data['url'], body=data,
                                headers=response.data['headers'])
        self.assertEqual(response.status, 200)  # the URL+headers work

    @patch('server.websockets.ws_client_send_delta_async')
    def test_complete_upload_happy_path(self, send_delta):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.create_and_init(owner=user)
        uuid = str(uuidgen.uuid4())
        key = f'wf-123/wfm-234/{uuid}.csv'
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            module_id_name='x',
            inprogress_file_upload_id=None,
            inprogress_file_upload_key=key,
            inprogress_file_upload_last_accessed_at=timezone.now(),
        )
        # The user needs to write the file to S3 before calling complete_upload
        minio.put_bytes(
            minio.UserFilesBucket,
            key,
            b'1234567',
            ContentDisposition="attachment; filename*=UTF-8''file.csv",
        )
        send_delta.side_effect = async_noop
        response = self.run_handler(complete_upload, user=user,
                                    workflow=workflow, wfModuleId=wf_module.id,
                                    key=key)
        self.assertEqual(response.error, '')
        self.assertEqual(response.data, {'uuid': uuid})
        wf_module.refresh_from_db()
        self.assertIsNone(wf_module.inprogress_file_upload_id)
        self.assertIsNone(wf_module.inprogress_file_upload_key)
        self.assertIsNone(wf_module.inprogress_file_upload_last_accessed_at)
        uploaded_file: UploadedFile = wf_module.uploaded_files.first()
        self.assertEqual(uploaded_file.name, 'file.csv')
        self.assertEqual(uploaded_file.uuid, uuid)
        self.assertEqual(uploaded_file.size, 7)
        self.assertEqual(uploaded_file.bucket, minio.UserFilesBucket)
        self.assertEqual(uploaded_file.key, key)

    def test_create_multipart_upload_happy_path(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.create_and_init(owner=user)
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            module_id_name='x',
        )

        response = self.run_handler(create_multipart_upload, user=user,
                                    workflow=workflow, wfModuleId=wf_module.id,
                                    filename='abc.csv')
        self.assertEqual(response.error, '')
        self.assertRegex(response.data['key'],
                         r'wf-\d+/wfm-\d+/[-a-f0-9]{36}.csv')
        self.assertIsInstance(response.data['uploadId'], str)
        wf_module.refresh_from_db()
        self.assertEqual(wf_module.inprogress_file_upload_id,
                         response.data['uploadId'])
        self.assertEqual(wf_module.inprogress_file_upload_key,
                         response.data['key'])
        self.assertIsNotNone(wf_module.inprogress_file_upload_last_accessed_at)

    def test_abort_multipart_upload_happy_path(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.create_and_init(owner=user)
        upload_id = minio.create_multipart_upload(minio.UserFilesBucket,
                                                  'key', 'file.csv')
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            module_id_name='x',
            inprogress_file_upload_id=upload_id,
            inprogress_file_upload_key='key',
            inprogress_file_upload_last_accessed_at=timezone.now()
        )

        response = self.run_handler(abort_multipart_upload, user=user,
                                    workflow=workflow, wfModuleId=wf_module.id,
                                    uploadId=upload_id)
        self.assertResponse(response, data=None)
        wf_module.refresh_from_db()
        self.assertIsNone(wf_module.inprogress_file_upload_id)
        self.assertIsNone(wf_module.inprogress_file_upload_key)
        self.assertIsNone(wf_module.inprogress_file_upload_last_accessed_at)
        with self.assertRaises(minio.error.NoSuchUpload):
            minio.abort_multipart_upload(minio.UserFilesBucket, 'key',
                                         upload_id)

    def test_abort_multipart_upload_upload_already_aborted(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.create_and_init(owner=user)
        upload_id = minio.create_multipart_upload(minio.UserFilesBucket,
                                                  'key', 'file.csv')
        minio.abort_multipart_upload(minio.UserFilesBucket, 'key', upload_id)
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            module_id_name='x',
            inprogress_file_upload_id=upload_id,
            inprogress_file_upload_key='key',
            inprogress_file_upload_last_accessed_at=timezone.now()
        )

        response = self.run_handler(abort_multipart_upload, user=user,
                                    workflow=workflow, wfModuleId=wf_module.id,
                                    uploadId=upload_id)
        self.assertResponse(response, data=None)
        # Must remove data from the DB even if the file isn't in minio.
        wf_module.refresh_from_db()
        self.assertIsNone(wf_module.inprogress_file_upload_id)
        self.assertIsNone(wf_module.inprogress_file_upload_key)
        self.assertIsNone(wf_module.inprogress_file_upload_last_accessed_at)

    @patch('server.websockets.ws_client_send_delta_async')
    def test_multipart_upload_by_presigned_requests(self, send_delta):
        """Test presign_upload_part _and_ complete_multipart_upload"""
        # Integration-test: use `urllib3` to run presigned responses.
        # See `test_minio` for canonical usage.
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.create_and_init(owner=user)
        uuid = str(uuidgen.uuid4())
        key = f'wf-123/wfm-234/{uuid}.csv'
        upload_id = minio.create_multipart_upload(minio.UserFilesBucket,
                                                  key, 'file.csv')
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            module_id_name='x',
            inprogress_file_upload_id=upload_id,
            inprogress_file_upload_key=key,
            inprogress_file_upload_last_accessed_at=timezone.now()
        )

        data = b'1234567' * 1024 * 1024  # 7MB => 5MB+2MB parts
        data1 = data[:5*1024*1024]
        data2 = data[5*1024*1024:]
        md5sum1 = _base64_md5sum(data1)
        md5sum2 = _base64_md5sum(data2)

        response1 = self.run_handler(presign_upload_part, user=user,
                                     workflow=workflow,
                                     wfModuleId=wf_module.id, uploadId=upload_id,
                                     partNumber=1, nBytes=len(data1),
                                     base64Md5sum=md5sum1)
        self.assertEqual(response1.error, '')
        response2 = self.run_handler(presign_upload_part, user=user,
                                     workflow=workflow,
                                     wfModuleId=wf_module.id,
                                     uploadId=upload_id, partNumber=2,
                                     nBytes=len(data2), base64Md5sum=md5sum2)
        self.assertEqual(response2.error, '')

        http = urllib3.PoolManager()
        s3response1 = http.request('PUT', response1.data['url'], body=data1,
                                   headers=response1.data['headers'])
        self.assertEqual(s3response1.status, 200)
        s3response2 = http.request('PUT', response2.data['url'], body=data2,
                                   headers=response2.data['headers'])
        self.assertEqual(s3response2.status, 200)

        etag1 = s3response1.headers['ETag'][1:-1]  # un-wrap quotes
        etag2 = s3response2.headers['ETag'][1:-1]  # un-wrap quotes
        send_delta.side_effect = async_noop
        response3 = self.run_handler(complete_multipart_upload, user=user,
                                     workflow=workflow,
                                     wfModuleId=wf_module.id,
                                     uploadId=upload_id, etags=[etag1, etag2])
        self.assertResponse(response3, data={'uuid': uuid})
        self.assertEqual(
            minio.get_object_with_data(minio.UserFilesBucket, key)['Body'],
            data
        )
