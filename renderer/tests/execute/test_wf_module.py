from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from uuid import uuid1
from django.utils import timezone
import pandas as pd
from pandas.testing import assert_frame_equal
from cjwkernel.pandas.types import ProcessResult
from server import minio, parquet
from server.models import LoadedModule, Workflow, WfModule, StoredObject
from server.models.param_dtype import ParamDType
from server.tests.utils import DbTestCase
from renderer.execute.wf_module import execute_wfmodule


async def noop(*args, **kwargs):
    return


class WfModuleTests(DbTestCase):
    def _store_fetched_table(
        self, wf_module: WfModule, table: pd.DataFrame
    ) -> StoredObject:
        key = str(uuid1())
        size = parquet.write(minio.StoredObjectsBucket, key, table)
        stored_object = wf_module.stored_objects.create(
            bucket=minio.StoredObjectsBucket,
            key=key,
            size=size,
            hash="this test ignores hashes",
        )
        wf_module.stored_data_version = stored_object.stored_at
        wf_module.save(update_fields=["stored_data_version"])
        return stored_object

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
        expected = "Please delete this step: an administrator uninstalled its code."
        self.assertEqual(result.error, expected)
        wf_module.refresh_from_db()
        self.assertEqual(wf_module.cached_render_result_error, expected)

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
        self._store_fetched_table(wf_module, pd.DataFrame({"A": [1]}))

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
        so = self._store_fetched_table(wf_module, pd.DataFrame({"A": [1]}))
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
        stored_object = self._store_fetched_table(wf_module, pd.DataFrame({"A": [1]}))
        # Now write an invalid (but realistic) Parquet file
        minio.fput_file(
            stored_object.bucket,
            stored_object.key,
            (
                Path(__file__).parent.parent.parent.parent
                / "server"
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
