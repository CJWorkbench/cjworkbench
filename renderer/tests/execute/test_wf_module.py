from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock, patch
from django.utils import timezone
import pyarrow
from cjwkernel.types import I18nMessage, RenderError, RenderResult
from cjwkernel.tests.util import parquet_file, assert_arrow_table_equals
from cjwstate import minio
from cjwstate.storedobjects import create_stored_object
from cjwstate.models import ModuleVersion, Workflow
from cjwstate.models.loaded_module import LoadedModule
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
            execute_wfmodule(
                workflow,
                wf_module,
                {},
                tab.to_arrow(),
                RenderResult(),
                {},
                Path("/unused"),
            )
        )
        expected = RenderResult(
            errors=[
                RenderError(
                    I18nMessage.TODO_i18n(
                        "Please delete this step: an administrator uninstalled its code."
                    )
                )
            ]
        )
        self.assertEqual(result, expected)
        wf_module.refresh_from_db()
        self.assertEqual(wf_module.cached_render_result.errors, expected.errors)

    @contextmanager
    def _stub_module(self, render_fn):
        mock_module = Mock(LoadedModule)
        mock_module.render.side_effect = render_fn
        ModuleVersion.create_or_replace_from_spec(
            {"id_name": "x", "name": "X", "category": "Clean", "parameters": []}
        )
        with patch.object(
            LoadedModule, "for_module_version_sync", lambda *a: mock_module
        ):
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
        with parquet_file({"A": [1]}) as path:
            so = create_stored_object(workflow.id, wf_module.id, path, "hash")
        wf_module.stored_data_version = so.stored_at
        wf_module.save(update_fields=["stored_data_version"])

        def render(*args, fetch_result, **kwargs):
            self.assertEqual(
                fetch_result.errors,
                [RenderError(I18nMessage.TODO_i18n("maybe an error"))],
            )
            assert_arrow_table_equals(
                pyarrow.parquet.read_table(str(fetch_result.path)), {"A": [1]}
            )
            return RenderResult()

        with self._stub_module(render):
            self.run_with_async_db(
                execute_wfmodule(
                    workflow,
                    wf_module,
                    {},
                    tab.name,
                    RenderResult(),
                    {},
                    Path("/unused"),
                )
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
        with parquet_file({"A": [1]}) as path:
            so = create_stored_object(workflow.id, wf_module.id, path, "hash")
        wf_module.stored_data_version = so.stored_at
        wf_module.save(update_fields=["stored_data_version"])
        # Now delete the file on S3 -- but leave the DB pointing to it.
        minio.remove(so.bucket, so.key)

        def render(*args, fetch_result, **kwargs):
            self.assertIsNone(fetch_result)
            return RenderResult()

        with self._stub_module(render):
            self.run_with_async_db(
                execute_wfmodule(
                    workflow,
                    wf_module,
                    {},
                    tab.name,
                    RenderResult(),
                    {},
                    Path("/unused"),
                )
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
            return RenderResult()

        with self._stub_module(render):
            self.run_with_async_db(
                execute_wfmodule(
                    workflow,
                    wf_module,
                    {},
                    tab.name,
                    RenderResult(),
                    {},
                    Path("/unused"),
                )
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
            return RenderResult()

        with self._stub_module(render):
            self.run_with_async_db(
                execute_wfmodule(
                    workflow,
                    wf_module,
                    {},
                    tab.name,
                    RenderResult(),
                    {},
                    Path("/unused"),
                )
            )
