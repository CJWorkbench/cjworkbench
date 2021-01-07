import unittest

from cjwstate.models.step import Step
from cjwstate.models.workflow import Workflow
from cjwstate.tests.utils import DbTestCaseWithModuleRegistry, create_module_zipfile
from cjwstate.upload import (
    UploadError,
    raise_if_api_token_is_wrong,
    locked_and_loaded_step,
)


def _init_module(id_name, param_id_name="file", param_type="file"):
    create_module_zipfile(
        id_name,
        spec_kwargs={"parameters": [{"id_name": param_id_name, "type": param_type}]},
    )


class LockedAndLoadedStepTest(DbTestCaseWithModuleRegistry):
    def test_workflow_not_found(self):
        with self.assertRaisesRegex(UploadError, "UploadError<404,workflow-not-found>"):
            with locked_and_loaded_step(999, "abc"):
                pass

    def test_step_not_found(self):
        workflow = Workflow.create_and_init()
        with self.assertRaisesRegex(UploadError, "UploadError<404,step-not-found>"):
            with locked_and_loaded_step(workflow.id, "abc"):
                pass

    def test_step_module_deleted(self):
        workflow = Workflow.create_and_init()
        workflow.tabs.first().steps.create(
            order=0,
            slug="step-123",
            module_id_name="doesnotexist",
            file_upload_api_token="abc123",
            params={"file": None},
        )
        with self.assertRaisesRegex(
            UploadError, "UploadError<400,step-module-deleted>"
        ):
            with locked_and_loaded_step(workflow.id, "step-123"):
                pass

    def test_step_module_has_no_file_param(self):
        _init_module("x", param_id_name="file", param_type="string")
        workflow = Workflow.create_and_init()
        workflow.tabs.first().steps.create(
            order=0,
            slug="step-123",
            module_id_name="x",
            file_upload_api_token="abc123",
            params={"file": None},
        )
        with self.assertRaisesRegex(
            UploadError, "UploadError<400,step-has-no-file-param>"
        ):
            with locked_and_loaded_step(workflow.id, "step-123"):
                pass

    def test_yielded_values(self):
        _init_module("x", param_id_name="file", param_type="file")
        workflow = Workflow.create_and_init()
        step = workflow.tabs.first().steps.create(
            order=0,
            slug="step-123",
            module_id_name="x",
            file_upload_api_token="abc123",
            params={"file": None},
        )
        with locked_and_loaded_step(workflow.id, "step-123") as x:
            self.assertEqual(x[0].workflow, workflow)
            self.assertEqual(x[1], step)
            self.assertEqual(x[2], "file")


class RaiseIfApiTokenIsWrongTest(unittest.TestCase):
    def test_step_has_no_api_token(self):
        step = Step(file_upload_api_token=None)
        with self.assertRaisesRegex(
            UploadError, "UploadError<403,step-has-no-api-token>"
        ):
            raise_if_api_token_is_wrong(step, "some-api-token")

    def test_step_has_different_api_token(self):
        step = Step(file_upload_api_token="good-api-token")
        with self.assertRaisesRegex(
            UploadError, "UploadError<403,authorization-bearer-token-invalid>"
        ):
            raise_if_api_token_is_wrong(step, "bad-api-token")

    def test_step_has_same_api_token(self):
        step = Step(file_upload_api_token="good-api-token")
        raise_if_api_token_is_wrong(step, "good-api-token")
