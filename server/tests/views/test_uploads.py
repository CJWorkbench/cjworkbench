import json
from unittest.mock import patch
from server import minio
from server.models import ModuleVersion, Workflow
from server.tests.utils import DbTestCase


async def async_noop(*args, **kwargs):
    pass


class MockLoadedModule:
    def __init__(self, *args):
        pass

    def migrate_params(self, values):
        return values


def _init_module(id_name, param_id_name="file", param_type="file"):
    ModuleVersion.create_or_replace_from_spec(
        {
            "id_name": id_name,
            "name": id_name,
            "category": "Clean",
            "parameters": [{"id_name": param_id_name, "type": param_type}],
        }
    )


class LoadsWfModuleForApiTest(DbTestCase):
    # All these tests _test_ loads_wf_module_for_api_upload, but the mechanism
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
        workflow.tabs.first().wf_modules.create(
            order=0, slug="step-123", module_id_name="x"
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
        workflow.tabs.first().wf_modules.create(
            order=0, slug="step-123", module_id_name="x", file_upload_api_token="abc123"
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
        workflow.tabs.first().wf_modules.create(
            order=0, slug="step-123", module_id_name="x", file_upload_api_token="abc123"
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
        workflow.tabs.first().wf_modules.create(
            order=0, slug="step-123", module_id_name="x", file_upload_api_token="abc123"
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


class UploadListTest(DbTestCase):
    def test_create_in_progress_upload(self):
        workflow = Workflow.create_and_init()
        _init_module("x")
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, slug="step-123", module_id_name="x", file_upload_api_token="abc123"
        )
        response = self.client.post(
            f"/api/v1/workflows/{workflow.id}/steps/step-123/uploads",
            HTTP_AUTHORIZATION="Bearer abc123",
        )
        self.assertEqual(response.status_code, 200)
        # Upload is created in the database
        upload = wf_module.in_progress_uploads.first()
        self.assertIsNotNone(upload)
        # Useful information is returned
        data = json.loads(response.content)
        self.assertRegexpMatches(data["key"], str(upload.id) + "$")
        self.assertEqual(data["uploadId"], str(upload.id))


class UploadTest(DbTestCase):
    def test_abort_missing_upload_is_404(self):
        _init_module("x")
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, slug="step-123", module_id_name="x", file_upload_api_token="abc123"
        )
        upload = wf_module.in_progress_uploads.create()
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
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, slug="step-123", module_id_name="x", file_upload_api_token="abc123"
        )
        upload = wf_module.in_progress_uploads.create(is_completed=True)
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
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, slug="step-123", module_id_name="x", file_upload_api_token="abc123"
        )
        upload = wf_module.in_progress_uploads.create()
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
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, slug="step-123", module_id_name="x", file_upload_api_token="abc123"
        )
        upload = wf_module.in_progress_uploads.create()
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
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, slug="step-123", module_id_name="x", file_upload_api_token="abc123"
        )
        upload = wf_module.in_progress_uploads.create()
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
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, slug="step-123", module_id_name="x", file_upload_api_token="abc123"
        )
        upload = wf_module.in_progress_uploads.create()
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
        workflow.tabs.first().wf_modules.create(
            order=0, slug="step-123", module_id_name="x", file_upload_api_token="abc123"
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
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, slug="step-123", module_id_name="x", file_upload_api_token="abc123"
        )
        upload = wf_module.in_progress_uploads.create(is_completed=True)
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
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, slug="step-123", module_id_name="x", file_upload_api_token="abc123"
        )
        upload = wf_module.in_progress_uploads.create()
        response = self.client.post(
            f"/api/v1/workflows/{workflow.id}/steps/step-123/uploads/{upload.id}",
            {"filename": "test.csv"},
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer abc123",
        )
        self.assertEqual(response.status_code, 409)
        error = json.loads(response.content)["error"]
        self.assertEqual(error["code"], "file-not-uploaded")

    @patch("server.websockets.ws_client_send_delta_async")
    @patch("server.rabbitmq.queue_render")
    @patch(
        "server.models.loaded_module.LoadedModule.for_module_version_sync",
        MockLoadedModule,
    )
    def test_complete_happy_path(self, queue_render, send_delta):
        send_delta.return_value = async_noop()
        queue_render.return_value = async_noop()
        _init_module("x")
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, slug="step-123", module_id_name="x", file_upload_api_token="abc123"
        )
        upload = wf_module.in_progress_uploads.create()
        uuid = str(upload.id)
        key = upload.get_upload_key()
        minio.put_bytes(upload.Bucket, key, b"1234567")
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
        uploaded_file = wf_module.uploaded_files.first()
        self.assertEqual(
            uploaded_file.key, f"wf-{workflow.id}/wfm-{wf_module.id}/{uuid}.csv"
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
        # Send deltas
        send_delta.assert_called()
        queue_render.assert_called()
