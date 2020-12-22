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


class LoadsStepForApiTest(DbTestCaseWithModuleRegistry):
    # All these tests _test_ loads_step_for_api_upload, but the mechanism
    # is UploadList.put() -- which we assume uses the decorator.
    def test_authorization_header_missing(self):
        response = self.client.post("/api/v1/workflows/999/steps/step-123/uploads")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            json.loads(response.content)["error"]["code"],
            "authorization-bearer-token-not-provided",
        )

    def test_authorization_header_not_bearer(self):
        response = self.client.post(
            "/api/v1/workflows/999/steps/step-123/uploads",
            HTTP_AUTHORIZATION="Basic YWxhZGRpbjpvcGVuc2VzYW1l",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            json.loads(response.content)["error"]["code"],
            "authorization-bearer-token-not-provided",
        )

    def test_workflow_not_found(self):
        response = self.client.post(
            "/api/v1/workflows/999/steps/step-123/uploads",
            HTTP_AUTHORIZATION="Bearer abc123",
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            json.loads(response.content)["error"]["code"], "workflow-not-found"
        )

    def test_step_not_found(self):
        workflow = Workflow.create_and_init()
        response = self.client.post(
            f"/api/v1/workflows/{workflow.id}/steps/step-123/uploads",
            HTTP_AUTHORIZATION="Bearer abc123",
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            json.loads(response.content)["error"]["code"], "step-not-found"
        )

    def test_step_has_no_api_token(self):
        _init_module("x")
        workflow = Workflow.create_and_init()
        workflow.tabs.first().steps.create(
            order=0, slug="step-123", module_id_name="x", params={"file": None}
        )
        response = self.client.post(
            f"/api/v1/workflows/{workflow.id}/steps/step-123/uploads",
            HTTP_AUTHORIZATION="Bearer abc123",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            json.loads(response.content)["error"]["code"], "step-has-no-api-token"
        )

    def test_step_has_no_module_version(self):
        workflow = Workflow.create_and_init()
        workflow.tabs.first().steps.create(
            order=0,
            slug="step-123",
            module_id_name="x",
            file_upload_api_token="abc123",
            params={"file": None},
        )
        response = self.client.post(
            f"/api/v1/workflows/{workflow.id}/steps/step-123/uploads",
            HTTP_AUTHORIZATION="Bearer abc123",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            json.loads(response.content)["error"]["code"], "step-module-deleted"
        )

    def test_step_module_has_no_file_param(self):
        _init_module("x", param_type="string")
        workflow = Workflow.create_and_init()
        workflow.tabs.first().steps.create(
            order=0,
            slug="step-123",
            module_id_name="x",
            file_upload_api_token="abc123",
            params={"file": None},
        )
        response = self.client.post(
            f"/api/v1/workflows/{workflow.id}/steps/step-123/uploads",
            HTTP_AUTHORIZATION="Bearer abc123",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            json.loads(response.content)["error"]["code"], "step-has-no-file-param"
        )

    def test_authorization_bearer_token_invalid(self):
        _init_module("x")
        workflow = Workflow.create_and_init()
        workflow.tabs.first().steps.create(
            order=0,
            slug="step-123",
            module_id_name="x",
            file_upload_api_token="abc123",
            params={"file": None},
        )
        response = self.client.post(
            f"/api/v1/workflows/{workflow.id}/steps/step-123/uploads",
            HTTP_AUTHORIZATION="Bearer abc123XXX",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            json.loads(response.content)["error"]["code"],
            "authorization-bearer-token-invalid",
        )


class UploadListTest(DbTestCaseWithModuleRegistry):
    def test_create_in_progress_upload(self):
        workflow = Workflow.create_and_init()
        _init_module("x")
        step = workflow.tabs.first().steps.create(
            order=0,
            slug="step-123",
            module_id_name="x",
            file_upload_api_token="abc123",
            params={"file": None},
        )
        response = self.client.post(
            f"/api/v1/workflows/{workflow.id}/steps/step-123/uploads",
            HTTP_AUTHORIZATION="Bearer abc123",
        )
        self.assertEqual(response.status_code, 200)
        # Upload is created in the database
        upload = step.in_progress_uploads.first()
        self.assertIsNotNone(upload)
        # Useful information is returned
        data = json.loads(response.content)
        self.assertRegexpMatches(data["key"], str(upload.id) + "$")
        self.assertRegexpMatches(data["finishUrl"], str(upload.id) + "$")


class UploadTest(DbTestCaseWithModuleRegistryAndMockKernel):
    def test_abort_missing_upload_is_404(self):
        _init_module("x")
        workflow = Workflow.create_and_init()
        step = workflow.tabs.first().steps.create(
            order=0,
            slug="step-123",
            module_id_name="x",
            file_upload_api_token="abc123",
            params={"file": None},
        )
        upload = step.in_progress_uploads.create()
        key = upload.get_upload_key()
        minio.put_bytes(upload.Bucket, key, b"1234567")
        response = self.client.delete(
            f"/api/v1/workflows/{workflow.id}/steps/step-123/uploads/dcc00084-812d-4769-bf77-94518f18ff3d",
            HTTP_AUTHORIZATION="Bearer abc123",
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            json.loads(response.content)["error"]["code"], "upload-not-found"
        )

    def test_abort_completed_upload_is_404(self):
        _init_module("x")
        workflow = Workflow.create_and_init()
        step = workflow.tabs.first().steps.create(
            order=0,
            slug="step-123",
            module_id_name="x",
            file_upload_api_token="abc123",
            params={"file": None},
        )
        upload = step.in_progress_uploads.create(is_completed=True)
        response = self.client.delete(
            f"/api/v1/workflows/{workflow.id}/steps/step-123/uploads/{upload.id}",
            HTTP_AUTHORIZATION="Bearer abc123",
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            json.loads(response.content)["error"]["code"], "upload-not-found"
        )

    def test_abort(self):
        _init_module("x")
        workflow = Workflow.create_and_init()
        step = workflow.tabs.first().steps.create(
            order=0,
            slug="step-123",
            module_id_name="x",
            file_upload_api_token="abc123",
            params={"file": None},
        )
        upload = step.in_progress_uploads.create()
        key = upload.get_upload_key()
        minio.put_bytes(upload.Bucket, key, b"1234567")
        response = self.client.delete(
            f"/api/v1/workflows/{workflow.id}/steps/step-123/uploads/{upload.id}",
            HTTP_AUTHORIZATION="Bearer abc123",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {})
        self.assertFalse(minio.exists(upload.Bucket, key))  # file was deleted
        upload.refresh_from_db()
        self.assertTrue(upload.is_completed)

    def test_complete_invalid_utf8(self):
        _init_module("x")
        workflow = Workflow.create_and_init()
        step = workflow.tabs.first().steps.create(
            order=0,
            slug="step-123",
            module_id_name="x",
            file_upload_api_token="abc123",
            params={"file": None},
        )
        upload = step.in_progress_uploads.create()
        response = self.client.post(
            f"/api/v1/workflows/{workflow.id}/steps/step-123/uploads/{upload.id}",
            '{"café": "latté"}'.encode("latin1"),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer abc123",
        )
        self.assertEqual(response.status_code, 400)
        error = json.loads(response.content)["error"]
        self.assertEqual(error["code"], "body-not-utf8")

    def test_complete_invalid_json(self):
        _init_module("x")
        workflow = Workflow.create_and_init()
        step = workflow.tabs.first().steps.create(
            order=0,
            slug="step-123",
            module_id_name="x",
            file_upload_api_token="abc123",
            params={"file": None},
        )
        upload = step.in_progress_uploads.create()
        response = self.client.post(
            f"/api/v1/workflows/{workflow.id}/steps/step-123/uploads/{upload.id}",
            b"{",
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer abc123",
        )
        self.assertEqual(response.status_code, 400)
        error = json.loads(response.content)["error"]
        self.assertEqual(error["code"], "body-not-json")

    def test_complete_json_form_error(self):
        _init_module("x")
        workflow = Workflow.create_and_init()
        step = workflow.tabs.first().steps.create(
            order=0,
            slug="step-123",
            module_id_name="x",
            file_upload_api_token="abc123",
            params={"file": None},
        )
        upload = step.in_progress_uploads.create()
        key = upload.get_upload_key()
        minio.put_bytes(upload.Bucket, key, b"1234567")
        response = self.client.post(
            f"/api/v1/workflows/{workflow.id}/steps/step-123/uploads/{upload.id}",
            {"filename": None},
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer abc123",
        )
        self.assertEqual(response.status_code, 400)
        error = json.loads(response.content)["error"]
        self.assertEqual(error["code"], "body-has-errors")
        self.assertIn("filename", error["errors"])

    def test_complete_upload_not_found(self):
        _init_module("x")
        workflow = Workflow.create_and_init()
        workflow.tabs.first().steps.create(
            order=0,
            slug="step-123",
            module_id_name="x",
            file_upload_api_token="abc123",
            params={"file": None},
        )
        response = self.client.post(
            f"/api/v1/workflows/{workflow.id}/steps/step-123/uploads/dcc00084-812d-4769-bf77-94518f18ff3d",
            {"filename": "test.csv"},
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer abc123",
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            json.loads(response.content)["error"]["code"], "upload-not-found"
        )

    def test_complete_completed_upload(self):
        _init_module("x")
        workflow = Workflow.create_and_init()
        step = workflow.tabs.first().steps.create(
            order=0,
            slug="step-123",
            module_id_name="x",
            file_upload_api_token="abc123",
            params={"file": None},
        )
        upload = step.in_progress_uploads.create(is_completed=True)
        response = self.client.post(
            f"/api/v1/workflows/{workflow.id}/steps/step-123/uploads/{upload.id}",
            {"filename": "test.csv"},
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer abc123",
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            json.loads(response.content)["error"]["code"], "upload-not-found"
        )

    def test_complete_file_not_found(self):
        _init_module("x")
        workflow = Workflow.create_and_init()
        step = workflow.tabs.first().steps.create(
            order=0,
            slug="step-123",
            module_id_name="x",
            file_upload_api_token="abc123",
            params={"file": None},
        )
        upload = step.in_progress_uploads.create()
        response = self.client.post(
            f"/api/v1/workflows/{workflow.id}/steps/step-123/uploads/{upload.id}",
            {"filename": "test.csv"},
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer abc123",
        )
        self.assertEqual(response.status_code, 409)
        error = json.loads(response.content)["error"]
        self.assertEqual(error["code"], "file-not-uploaded")

    @patch.object(rabbitmq, "send_update_to_workflow_clients")
    @patch.object(rabbitmq, "queue_render")
    def test_complete_happy_path(self, queue_render, send_update):
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
        upload = step.in_progress_uploads.create()
        uuid = str(upload.id)
        key = upload.get_upload_key()
        minio.put_bytes(upload.Bucket, key, b"1234567")
        with self.assertLogs(level=logging.INFO):
            # Logs SetStepParams's migrate_params()
            response = self.client.post(
                f"/api/v1/workflows/{workflow.id}/steps/step-123/uploads/{upload.id}",
                {"filename": "test.csv"},
                content_type="application/json",
                HTTP_AUTHORIZATION="Bearer abc123",
            )
        self.assertEqual(response.status_code, 200)
        # Upload and its S3 data were deleted
        self.assertFalse(minio.exists(upload.Bucket, key))
        upload.refresh_from_db()
        self.assertTrue(upload.is_completed)
        # Final upload was created
        uploaded_file = step.uploaded_files.first()
        self.assertEqual(
            uploaded_file.key, f"wf-{workflow.id}/wfm-{step.id}/{uuid}.csv"
        )
        self.assertEqual(
            minio.get_object_with_data(minio.UserFilesBucket, uploaded_file.key)[
                "Body"
            ],
            b"1234567",
        )
        self.assertEqual(uploaded_file.name, "test.csv")
        # Return value includes uuid
        data = json.loads(response.content)
        self.assertEqual(data["uuid"], uuid)
        self.assertEqual(data["name"], "test.csv")
        self.assertEqual(data["size"], 7)
        # SetStepParams ran
        step.refresh_from_db()
        self.assertEqual(step.params, {"file": uuid})
        # Send deltas
        send_update.assert_called()
        self.assertEqual(
            send_update.mock_calls[0][1][1].steps[step.id].files,
            [
                clientside.UploadedFile(
                    name="test.csv",
                    uuid=uuid,
                    size=7,
                    created_at=uploaded_file.created_at,
                )
            ],
        )
        queue_render.assert_called()

    @override_settings(MAX_N_FILES_PER_STEP=2)
    @patch.object(rabbitmq, "send_update_to_workflow_clients", async_noop)
    @patch.object(rabbitmq, "queue_render", async_noop)
    def test_complete_enforce_storage_limits(self):
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
        upload = step.in_progress_uploads.create()
        uuid = str(upload.id)
        key = upload.get_upload_key()
        minio.put_bytes(upload.Bucket, key, b"4444")
        with self.assertLogs(level=logging.INFO):
            # Logs SetStepParams's migrate_params()
            response = self.client.post(
                f"/api/v1/workflows/{workflow.id}/steps/step-123/uploads/{upload.id}",
                {"filename": "file4.txt"},
                content_type="application/json",
                HTTP_AUTHORIZATION="Bearer abc123",
            )
        self.assertEqual(response.status_code, 200)

        # Test excess uploaded files were deleted
        self.assertEqual(
            list(step.uploaded_files.order_by("id").values_list("name", flat=True)),
            ["file3.txt", "file4.txt"],
        )
        self.assertFalse(minio.exists(minio.UserFilesBucket, "foo/1.txt"))
        self.assertFalse(minio.exists(minio.UserFilesBucket, "foo/2.txt"))
