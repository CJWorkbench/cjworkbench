import logging

import httpx
from django.test import override_settings

from cjwstate.models import Workflow
from cjwstate.tests.utils import DbTestCaseWithModuleRegistry, create_module_zipfile


def _init_module(id_name, param_id_name="file", param_type="file"):
    create_module_zipfile(
        id_name,
        spec_kwargs={"parameters": [{"id_name": param_id_name, "type": param_type}]},
    )


class FilesTest(DbTestCaseWithModuleRegistry):
    def test_create(self):
        workflow = Workflow.create_and_init()
        _init_module("x")
        step = workflow.tabs.first().steps.create(
            order=0,
            slug="step-123",
            module_id_name="x",
            file_upload_api_token="abc123",
            params={"file": None},
        )
        with self.assertLogs("httpx._client", level=logging.DEBUG):
            response = self.client.post(
                f"/api/v1/workflows/{workflow.id}/steps/step-123/files",
                HTTP_AUTHORIZATION="Bearer abc123",
                content_type="application/json",
                data={"filename": "foo bar.csv", "size": 12345},
            )
        self.assertEqual(response.status_code, 200)

        tus_upload_url = response.json()["tusUploadUrl"]

        # Upload was created on tusd
        with self.assertLogs("httpx._client", level=logging.DEBUG):
            response = httpx.head(tus_upload_url, headers={"Tus-Resumable": "1.0.0"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Tus-Resumable"], "1.0.0")
        self.assertEqual(response.headers["Upload-Length"], "12345")
        # "Zm9vIGJhci5jc3Y=": "foo bar.csv"
        self.assertIn("filename Zm9vIGJhci5jc3Y=", response.headers["Upload-Metadata"])
        # "c3RlcC0xMjM=": "step-123"
        self.assertIn("stepSlug c3RlcC0xMjM=", response.headers["Upload-Metadata"])
        # "YWJjMTIz": "abc123"
        self.assertIn("apiToken YWJjMTIz", response.headers["Upload-Metadata"])

    def test_create_error_loading_step(self):
        workflow = Workflow.create_and_init()
        _init_module("x", param_type="string")
        step = workflow.tabs.first().steps.create(
            order=0,
            slug="step-123",
            module_id_name="x",
            file_upload_api_token="abc123",
            params={"file": None},
        )
        response = self.client.post(
            f"/api/v1/workflows/{workflow.id}/steps/step-123/files",
            HTTP_AUTHORIZATION="Bearer abc123",
            content_type="application/json",
            data={"filename": "foo bar.csv", "size": 12345},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": {"code": "step-has-no-file-param"}})

    def test_create_missing_api_token(self):
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
            f"/api/v1/workflows/{workflow.id}/steps/step-123/files",
            content_type="application/json",
            data={"filename": "foo bar.csv", "size": 12345},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json(),
            {"error": {"code": "authorization-bearer-token-not-provided"}},
        )

    def test_create_invalid_api_token(self):
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
            f"/api/v1/workflows/{workflow.id}/steps/step-123/files",
            HTTP_AUTHORIZATION="Bearer abc1234",
            content_type="application/json",
            data={"filename": "foo bar.csv", "size": 12345},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json(),
            {"error": {"code": "authorization-bearer-token-invalid"}},
        )

    def test_create_module_has_no_api_token(self):
        workflow = Workflow.create_and_init()
        _init_module("x")
        step = workflow.tabs.first().steps.create(
            order=0,
            slug="step-123",
            module_id_name="x",
            file_upload_api_token=None,
            params={"file": None},
        )
        response = self.client.post(
            f"/api/v1/workflows/{workflow.id}/steps/step-123/files",
            HTTP_AUTHORIZATION="Bearer abc1234",
            content_type="application/json",
            data={"filename": "foo bar.csv", "size": 12345},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {"error": {"code": "step-has-no-api-token"}})

    def test_create_body_not_utf8(self):
        response = self.client.post(
            f"/api/v1/workflows/1/steps/step-123/files",
            HTTP_AUTHORIZATION="Bearer abc1234",
            content_type="application/json",
            data=b'{"f\xe9": "bar"}',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": {"code": "body-not-utf8"}})

    def test_create_body_not_json(self):
        response = self.client.post(
            f"/api/v1/workflows/1/steps/step-123/files",
            HTTP_AUTHORIZATION="Bearer abc1234",
            content_type="application/json",
            data="this-is-not-json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": {"code": "body-not-json"}})

    def test_create_size_not_int(self):
        response = self.client.post(
            f"/api/v1/workflows/1/steps/step-123/files",
            HTTP_AUTHORIZATION="Bearer abc1234",
            content_type="application/json",
            data={"filename": "test.csv", "size": -123},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {
                "error": {
                    "code": "body-has-errors",
                    "errors": {
                        "size": [
                            {
                                "code": "min_value",
                                "message": "Ensure this value is greater than or equal to 0.",
                            }
                        ]
                    },
                }
            },
        )

    @override_settings(MAX_BYTES_FILES_PER_STEP=12345)
    def test_create_file_too_large(self):
        response = self.client.post(
            f"/api/v1/workflows/1/steps/step-123/files",
            HTTP_AUTHORIZATION="Bearer abc1234",
            content_type="application/json",
            data={"filename": "test.csv", "size": 123456},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {
                "error": {
                    "code": "body-has-errors",
                    "errors": {
                        "size": [
                            {
                                "code": "max_value",
                                "message": "Ensure this value is less than or equal to 12345.",
                            }
                        ]
                    },
                }
            },
        )

    @override_settings(MAX_BYTES_FILES_PER_STEP=12345)
    def test_create_file_too_large(self):
        response = self.client.post(
            f"/api/v1/workflows/1/steps/step-123/files",
            HTTP_AUTHORIZATION="Bearer abc1234",
            content_type="application/json",
            data={"filename": "test.csv", "size": 123456},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {
                "error": {
                    "code": "body-has-errors",
                    "errors": {
                        "size": [
                            {
                                "code": "max_value",
                                "message": "Ensure this value is less than or equal to 12345.",
                            }
                        ]
                    },
                }
            },
        )
