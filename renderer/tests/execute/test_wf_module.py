from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from django.utils import timezone
import pandas as pd
from pandas.testing import assert_frame_equal
from cjwkernel.pandas.types import ProcessResult
from cjwkernel.types import I18nMessage, RenderError
from cjwstate import minio
from cjwstate.storedobjects import create_stored_object
from cjwstate.models import Workflow
from cjwstate.models.loaded_module import LoadedModule
from cjwstate.models.param_dtype import ParamDType
from cjwstate.tests.utils import DbTestCase
from renderer.execute.wf_module import execute_wfmodule


async def noop(*args, **kwargs):
    return


class WfModuleTests(DbTestCase):
    @patch("server.websockets.ws_client_send_delta_async", noop)
    def test_deleted_module(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wf_module = tab.wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="deleted_module",
            last_relevant_delta_id=workflow.last_delta_id,
        )
        result = self.run_with_async_db(
            execute_wfmodule(workflow, wf_module, {}, tab.name, ProcessResult(), {})
        )
        expected = [
            RenderError(
                I18nMessage(
                    "TODO_i18n",
                    ["Please delete this step: an administrator uninstalled its code."],
                )
            )
        ]
        self.assertEqual(result.to_arrow("unused").errors, expected)
        wf_module.refresh_from_db()
        self.assertEqual(wf_module.cached_render_result.errors, expected)

    @contextmanager
    def _stub_module(self, render_fn):
        mock_module = LoadedModule("x", "x", ParamDType.Dict({}), render_impl=render_fn)
        with patch.object(
            LoadedModule, "for_module_version_sync", lambda *a: mock_module
        ):
            with self.assertLogs():  # eat log messages
                yield

    @patch("server.websockets.ws_client_send_delta_async", noop)
    def test_fetch_result_happy_path(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wf_module = tab.wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id,
            fetch_error="maybe an error",
        )
        create_stored_object(workflow, wf_module, pd.DataFrame({"A": [1]}), "hash")

        def render(*args, fetch_result, **kwargs):
            self.assertEqual(fetch_result.error, "maybe an error")
            assert_frame_equal(fetch_result.dataframe, pd.DataFrame({"A": [1]}))

        with self._stub_module(render):
            self.run_with_async_db(
                execute_wfmodule(workflow, wf_module, {}, tab.name, ProcessResult(), {})
            )

    @patch("server.websockets.ws_client_send_delta_async", noop)
    def test_fetch_result_deleted_file_means_none(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wf_module = tab.wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id,
        )
        so = create_stored_object(workflow, wf_module, pd.DataFrame({"A": [1]}), "hash")
        # Now delete the file on S3 -- but leave the DB pointing to it.
        minio.remove(so.bucket, so.key)

        def render(*args, fetch_result, **kwargs):
            self.assertIsNone(fetch_result)

        with self._stub_module(render):
            self.run_with_async_db(
                execute_wfmodule(workflow, wf_module, {}, tab.name, ProcessResult(), {})
            )

    @patch("server.websockets.ws_client_send_delta_async", noop)
    def test_fetch_result_invalid_parquet_means_none(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wf_module = tab.wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id,
        )
        stored_object = create_stored_object(
            workflow, wf_module, pd.DataFrame({"A": [1]}), "hash"
        )
        # Now write an invalid (but realistic) Parquet file
        minio.fput_file(
            stored_object.bucket,
            stored_object.key,
            (
                Path(__file__).parent.parent.parent.parent
                / "cjwstate"
                / "tests"
                / "test_data"
                / "fastparquet-issue-375.par"
            ),
        )

        def render(*args, fetch_result, **kwargs):
            self.assertIsNone(fetch_result)

        with self._stub_module(render):
            self.run_with_async_db(
                execute_wfmodule(workflow, wf_module, {}, tab.name, ProcessResult(), {})
            )

    @patch("server.websockets.ws_client_send_delta_async", noop)
    def test_fetch_result_deleted_stored_object_means_none(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wf_module = tab.wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id,
            # wf_module.stored_data_version is buggy: it can point at a nonexistent
            # StoredObject. Let's do that.
            stored_data_version=timezone.now(),
        )

        def render(*args, fetch_result, **kwargs):
            self.assertIsNone(fetch_result)

        with self._stub_module(render):
            self.run_with_async_db(
                execute_wfmodule(workflow, wf_module, {}, tab.name, ProcessResult(), {})
            )

    @patch("server.websockets.ws_client_send_delta_async", noop)
    def test_fetch_result_no_stored_object_means_none(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wf_module = tab.wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id,
        )

        def render(*args, fetch_result, **kwargs):
            self.assertIsNone(fetch_result)

        with self._stub_module(render):
            self.run_with_async_db(
                execute_wfmodule(workflow, wf_module, {}, tab.name, ProcessResult(), {})
            )
