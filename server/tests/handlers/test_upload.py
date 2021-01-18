import httpx
from django.contrib.auth.models import User
from django.test.utils import override_settings
from django.utils import timezone

from cjwstate import s3, rabbitmq
from cjwstate.models import Workflow
from server.handlers.upload import create_upload

from .util import HandlerTestCase

from cjwstate.tests.utils import (
    DbTestCaseWithModuleRegistryAndMockKernel,
    create_module_zipfile,
)


async def async_noop(*args, **kwargs):
    pass


class UploadTest(HandlerTestCase, DbTestCaseWithModuleRegistryAndMockKernel):
    def test_create_upload(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        create_module_zipfile(
            "x", spec_kwargs={"parameters": [{"id_name": "foo", "type": "file"}]}
        )
        step = workflow.tabs.first().steps.create(
            order=0, slug="step-1", module_id_name="x"
        )
        response = self.run_handler(
            create_upload,
            user=user,
            workflow=workflow,
            stepSlug="step-1",
            filename="test.csv",
            size=1234,
        )
        self.assertEqual(response.error, "")
        # Test that response has tusUploadUrl
        tus_upload_url = response.data["tusUploadUrl"]
        self.assertRegex(tus_upload_url, "http://testtusd:8080/files/[0-9a-z]+")

        # Upload was created on tusd
        response = httpx.head(tus_upload_url, headers={"Tus-Resumable": "1.0.0"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Tus-Resumable"], "1.0.0")
        self.assertEqual(response.headers["Upload-Length"], "1234")
        # "dGVzdC5jc3Y=" = "test.csv"
        self.assertIn("filename dGVzdC5jc3Y=", response.headers["Upload-Metadata"])
        # "c3RlcC0x": "step-1"
        self.assertIn("stepSlug c3RlcC0x", response.headers["Upload-Metadata"])
        # apiToken should be empty
        self.assertRegex(response.headers["Upload-Metadata"], "apiToken ?(?:$|,)")
