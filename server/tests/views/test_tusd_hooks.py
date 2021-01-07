import datetime
import json
import logging
from unittest.mock import patch

from django.test import override_settings

from cjwstate import clientside, minio, rabbitmq
from cjwstate.models import ModuleVersion, Workflow
from cjwstate.tests.utils import (
    DbTestCaseWithModuleRegistry,
    DbTestCaseWithModuleRegistryAndMockKernel,
    create_module_zipfile,
)


async def async_noop(*args, **kwargs):
    pass


def _init_module(id_name, param_id_name="file", param_type="file"):
    create_module_zipfile(
        id_name,
        spec_kwargs={"parameters": [{"id_name": param_id_name, "type": param_type}]},
    )


class UploadTest(DbTestCaseWithModuleRegistryAndMockKernel):
    @patch.object(rabbitmq, "send_update_to_workflow_clients")
    @patch.object(rabbitmq, "queue_render")
    def test_pre_finish_happy_path(self, queue_render, send_update):
        send_update.side_effect = async_noop
        queue_render.side_effect = async_noop
        _init_module("x")
        self.kernel.migrate_params.side_effect = lambda m, p: p
        workflow = Workflow.create_and_init()
        step = workflow.tabs.first().steps.create(
            order=0,
            slug="step-123",
            module_id_name="x",
            file_upload_api_token="abc123",
            params={"file": None},
        )
        minio.put_bytes(minio.TusUploadBucket, "data", b"1234567")
        with self.assertLogs(level=logging.INFO):
            # Logs SetStepParams's migrate_params()
            response = self.client.post(
                f"/tusd-hooks",
                {
                    "Upload": {
                        "MetaData": {
                            "filename": "foo.csv",
                            "workflowId": str(workflow.id),
                            "stepSlug": step.slug,
                            "apiToken": "abc123",
                        },
                        "Size": 7,
                        "Storage": {"Bucket": minio.TusUploadBucket, "Key": "data"},
                    }
                },
                HTTP_HOOK_NAME="pre-finish",
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {})
        # File was created
        uploaded_file = step.uploaded_files.first()
        self.assertRegex(
            uploaded_file.key, f"^wf-{workflow.id}/wfm-{step.id}/[-0-9a-f]{{36}}\\.csv$"
        )
        self.assertEqual(
            minio.get_object_with_data(minio.UserFilesBucket, uploaded_file.key)[
                "Body"
            ],
            b"1234567",
        )
        self.assertEqual(uploaded_file.name, "foo.csv")
        # SetStepParams ran
        uuid = uploaded_file.key[-40:-4]
        step.refresh_from_db()
        self.assertEqual(step.params, {"file": uuid})
        # Send deltas
        send_update.assert_called()
        self.assertEqual(
            send_update.mock_calls[0][1][1].steps[step.id].files,
            [
                clientside.UploadedFile(
                    name="foo.csv",
                    uuid=uuid,
                    size=7,
                    created_at=uploaded_file.created_at,
                )
            ],
        )
        queue_render.assert_called()

    @override_settings(MAX_N_FILES_PER_STEP=2)
    @patch.object(rabbitmq, "send_update_to_workflow_clients")
    @patch.object(rabbitmq, "queue_render", async_noop)
    def test_pre_finish_enforce_storage_limits(self, send_update):
        send_update.side_effect = async_noop

        _init_module("x")
        self.kernel.migrate_params.side_effect = lambda m, p: p
        workflow = Workflow.create_and_init()
        step = workflow.tabs.first().steps.create(
            order=0,
            slug="step-123",
            module_id_name="x",
            file_upload_api_token="abc123",
            params={"file": None},
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

        # Upload the new file, "file4.txt"
        minio.put_bytes(minio.TusUploadBucket, "new-key", b"4444")
        with self.assertLogs(level=logging.INFO):
            # Logs SetStepParams's migrate_params()
            response = self.client.post(
                f"/tusd-hooks",
                {
                    "Upload": {
                        "MetaData": {
                            "filename": "file4.txt",
                            "workflowId": str(workflow.id),
                            "stepSlug": step.slug,
                            "apiToken": "abc123",
                        },
                        "Size": 7,
                        "Storage": {"Bucket": minio.TusUploadBucket, "Key": "new-key"},
                    }
                },
                HTTP_HOOK_NAME="pre-finish",
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 200)

        # Test excess uploaded files were deleted
        self.assertEqual(
            list(step.uploaded_files.order_by("id").values_list("name", flat=True)),
            ["file3.txt", "file4.txt"],
        )
        self.assertFalse(minio.exists(minio.UserFilesBucket, "foo/1.txt"))
        self.assertFalse(minio.exists(minio.UserFilesBucket, "foo/2.txt"))

        # Test delta nixes old files from clients' browsers
        send_update.assert_called()
        uploaded_file = step.uploaded_files.get(name="file4.txt")
        self.assertEqual(
            send_update.mock_calls[0][1][1].steps[step.id].files,
            [
                clientside.UploadedFile(
                    name="file4.txt",
                    uuid=uploaded_file.uuid,
                    size=7,
                    created_at=uploaded_file.created_at,
                ),
                clientside.UploadedFile(
                    name="file3.txt",
                    uuid="df46244d-268a-0003-9b47-360502dd9b32",
                    size=3,
                    created_at=datetime.datetime(
                        2020, 1, 3, tzinfo=datetime.timezone.utc
                    ),
                ),
            ],
        )

    @patch.object(rabbitmq, "send_update_to_workflow_clients", async_noop)
    @patch.object(rabbitmq, "queue_render", async_noop)
    def test_pre_finish_no_op_when_api_token_is_off(self):
        _init_module("x")
        self.kernel.migrate_params.side_effect = lambda m, p: p
        workflow = Workflow.create_and_init()
        step = workflow.tabs.first().steps.create(
            order=0,
            slug="step-123",
            module_id_name="x",
            file_upload_api_token="abc123",
            params={"file": None},
        )
        minio.put_bytes(minio.TusUploadBucket, "data", b"1234567")
        response = self.client.post(
            f"/tusd-hooks",
            {
                "Upload": {
                    "MetaData": {
                        "filename": "foo.csv",
                        "workflowId": str(workflow.id),
                        "stepSlug": step.slug,
                        "apiToken": "an-out-of-date-token",
                    },
                    "Size": 7,
                    "Storage": {"Bucket": minio.TusUploadBucket, "Key": "data"},
                }
            },
            HTTP_HOOK_NAME="pre-finish",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json(), {"error": {"code": "authorization-bearer-token-invalid"}}
        )
        # File was not created
        self.assertEqual(0, step.uploaded_files.count())
