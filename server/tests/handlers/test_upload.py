import datetime
import hashlib
from base64 import b64encode
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test.utils import override_settings
from django.utils import timezone

from cjwstate import minio, rabbitmq
from cjwstate.models import Workflow
from server.handlers.upload import abort_upload, create_upload, finish_upload

from .util import HandlerTestCase


def _base64_md5sum(b: bytes) -> str:
    h = hashlib.md5()
    h.update(b)
    md5sum = h.digest()
    return b64encode(md5sum).decode("ascii")


async def async_noop(*args, **kwargs):
    pass


class UploadTest(HandlerTestCase):
    def test_create_upload(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        step = workflow.tabs.first().steps.create(
            order=0, slug="step-1", module_id_name="x"
        )
        response = self.run_handler(
            create_upload, user=user, workflow=workflow, stepId=step.id
        )
        self.assertEqual(response.error, "")
        # Test that step is aware of the upload
        in_progress_upload = step.in_progress_uploads.first()
        self.assertIsNotNone(in_progress_upload)
        self.assertRegex(
            in_progress_upload.get_upload_key(),
            "wf-%d/wfm-%d/upload_[-0-9a-f]{36}" % (workflow.id, step.id),
        )
        self.assertLessEqual(in_progress_upload.updated_at, timezone.now())
        # Test that response has bucket+key+credentials
        self.assertEqual(response.data["bucket"], minio.UserFilesBucket)
        self.assertEqual(response.data["key"], in_progress_upload.get_upload_key())
        self.assertIn("credentials", response.data)

    @patch.object(rabbitmq, "send_update_to_workflow_clients")
    def test_finish_upload_happy_path(self, send_update):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        step = workflow.tabs.first().steps.create(
            order=0, slug="step-1", module_id_name="x"
        )
        in_progress_upload = step.in_progress_uploads.create(
            id="147a9f5d-5b3e-41c3-a968-a84a5a9d587f"
        )
        key = in_progress_upload.get_upload_key()
        minio.put_bytes(in_progress_upload.Bucket, key, b"1234567")
        send_update.side_effect = async_noop
        response = self.run_handler(
            finish_upload,
            user=user,
            workflow=workflow,
            stepId=step.id,
            key=key,
            filename="test sheet.csv",
        )
        self.assertResponse(
            response, data={"uuid": "147a9f5d-5b3e-41c3-a968-a84a5a9d587f"}
        )
        # The uploaded file is deleted
        self.assertFalse(minio.exists(in_progress_upload.Bucket, key))
        # A new upload is created
        uploaded_file = step.uploaded_files.first()
        self.assertEqual(uploaded_file.name, "test sheet.csv")
        self.assertEqual(uploaded_file.size, 7)
        self.assertEqual(uploaded_file.uuid, "147a9f5d-5b3e-41c3-a968-a84a5a9d587f")
        final_key = (
            f"wf-{workflow.id}/wfm-{step.id}/147a9f5d-5b3e-41c3-a968-a84a5a9d587f.csv"
        )
        self.assertEqual(uploaded_file.key, final_key)
        # The file has the right bytes and metadata
        self.assertEqual(
            minio.get_object_with_data(minio.UserFilesBucket, final_key)["Body"],
            b"1234567",
        )
        self.assertEqual(
            minio.client.head_object(Bucket=minio.UserFilesBucket, Key=final_key)[
                "ContentDisposition"
            ],
            "attachment; filename*=UTF-8''test%20sheet.csv",
        )
        # step is updated
        send_update.assert_called()

    @override_settings(MAX_N_FILES_PER_STEP=2)
    @patch.object(rabbitmq, "send_update_to_workflow_clients")
    def test_finish_upload_enforce_storage_limits(self, send_update):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        step = workflow.tabs.first().steps.create(
            order=0, slug="step-1", module_id_name="x"
        )
        minio.put_bytes(minio.UserFilesBucket, "foo/1.txt", b"1")
        step.uploaded_files.create(
            created_at=datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc),
            name="file1.txt",
            size=1,
            uuid="df46244d-268a-0001-9b47-360502dd9b32",
            key="foo/1.txt",
        )
        minio.put_bytes(minio.UserFilesBucket, "foo/2.txt", b"22")
        step.uploaded_files.create(
            created_at=datetime.datetime(2020, 1, 2, tzinfo=datetime.timezone.utc),
            name="file2.txt",
            size=2,
            uuid="df46244d-268a-0002-9b47-360502dd9b32",
            key="foo/2.txt",
        )
        minio.put_bytes(minio.UserFilesBucket, "foo/3.txt", b"333")
        step.uploaded_files.create(
            created_at=datetime.datetime(2020, 1, 3, tzinfo=datetime.timezone.utc),
            name="file3.txt",
            size=3,
            uuid="df46244d-268a-0003-9b47-360502dd9b32",
            key="foo/3.txt",
        )
        in_progress_upload = step.in_progress_uploads.create(
            id="147a9f5d-5b3e-41c3-a968-a84a5a9d587f"
        )
        key = in_progress_upload.get_upload_key()
        minio.put_bytes(in_progress_upload.Bucket, key, b"1234567")
        send_update.side_effect = async_noop
        response = self.run_handler(
            finish_upload,
            user=user,
            workflow=workflow,
            stepId=step.id,
            key=key,
            filename="file4.txt",
        )
        self.assertResponse(
            response, data={"uuid": "147a9f5d-5b3e-41c3-a968-a84a5a9d587f"}
        )
        # Test excess uploaded files were deleted
        self.assertEqual(
            list(step.uploaded_files.order_by("id").values_list("name", flat=True)),
            ["file3.txt", "file4.txt"],
        )
        self.assertFalse(minio.exists(minio.UserFilesBucket, "foo/1.txt"))
        self.assertFalse(minio.exists(minio.UserFilesBucket, "foo/2.txt"))
        # The uploaded file is deleted
        self.assertFalse(minio.exists(in_progress_upload.Bucket, key))

        # step is updated
        send_update.assert_called()
        self.assertEqual(
            [f.name for f in send_update.mock_calls[0][1][1].steps[step.id].files],
            ["file4.txt", "file3.txt"],
        )

    def test_finish_upload_error_not_started(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        step = workflow.tabs.first().steps.create(
            order=0, slug="step-1", module_id_name="x"
        )
        in_progress_upload = step.in_progress_uploads.create(
            id="147a9f5d-5b3e-41c3-a968-a84a5a9d587f", is_completed=True
        )
        key = in_progress_upload.get_upload_key()
        response = self.run_handler(
            finish_upload,
            user=user,
            workflow=workflow,
            stepId=step.id,
            key=key,
            filename="test.csv",
        )
        self.assertResponse(
            response,
            error=(
                "BadRequest: key is not being uploaded for this Step right now. "
                "(Even a valid key becomes invalid after you create, finish or abort "
                "an upload on its Step.)"
            ),
        )

    def test_finish_upload_error_completed(self):
        # Appears to the user just like "not started"
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        step = workflow.tabs.first().steps.create(
            order=0, slug="step-1", module_id_name="x"
        )
        key = f"wf-{workflow.id}/wfm-{step.id}/upload_147a9f5d-5b3e-41c3-a968-a84a5a9d587f"
        response = self.run_handler(
            finish_upload,
            user=user,
            workflow=workflow,
            stepId=step.id,
            key=key,
            filename="test.csv",
        )
        self.assertResponse(
            response,
            error=(
                "BadRequest: key is not being uploaded for this Step right now. "
                "(Even a valid key becomes invalid after you create, finish or abort "
                "an upload on its Step.)"
            ),
        )

    def test_finish_upload_error_file_missing(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        step = workflow.tabs.first().steps.create(
            order=0, slug="step-1", module_id_name="x"
        )
        in_progress_upload = step.in_progress_uploads.create(
            id="147a9f5d-5b3e-41c3-a968-a84a5a9d587f"
        )
        key = in_progress_upload.get_upload_key()
        response = self.run_handler(
            finish_upload,
            user=user,
            workflow=workflow,
            stepId=step.id,
            key=key,
            filename="test.csv",
        )
        self.assertResponse(
            response,
            error=(
                "BadRequest: file not found. "
                "You must upload the file before calling finish_upload."
            ),
        )

    def test_abort_upload_happy_path_before_complete(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        step = workflow.tabs.first().steps.create(
            order=0, slug="step-1", module_id_name="x"
        )
        in_progress_upload = step.in_progress_uploads.create(
            id="147a9f5d-5b3e-41c3-a968-a84a5a9d587f"
        )
        key = in_progress_upload.get_upload_key()

        # precondition: there's an incomplete multipart upload. minio is a bit
        # different from S3 here, so we add a .assertIn to verify that the data
        # is there _before_ we abort.
        minio.client.create_multipart_upload(Bucket=in_progress_upload.Bucket, Key=key)
        response = minio.client.list_multipart_uploads(
            Bucket=in_progress_upload.Bucket, Prefix=key
        )
        self.assertIn("Uploads", response)

        response = self.run_handler(
            abort_upload, user=user, workflow=workflow, stepId=step.id, key=key
        )
        self.assertResponse(response, data=None)
        response = minio.client.list_multipart_uploads(
            Bucket=in_progress_upload.Bucket, Prefix=key
        )
        self.assertNotIn("Uploads", response)

        in_progress_upload.refresh_from_db()
        self.assertEqual(in_progress_upload.is_completed, True)

    def test_abort_upload_happy_path_after_complete(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        step = workflow.tabs.first().steps.create(
            order=0, slug="step-1", module_id_name="x"
        )
        in_progress_upload = step.in_progress_uploads.create(
            id="147a9f5d-5b3e-41c3-a968-a84a5a9d587f"
        )
        key = in_progress_upload.get_upload_key()
        minio.put_bytes(in_progress_upload.Bucket, key, b"1234567")
        response = self.run_handler(
            abort_upload, user=user, workflow=workflow, stepId=step.id, key=key
        )
        self.assertResponse(response, data=None)
        step.refresh_from_db()
        self.assertFalse(minio.exists(in_progress_upload.Bucket, key))
