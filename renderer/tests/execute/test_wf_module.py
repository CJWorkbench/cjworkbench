import contextlib
import logging
from unittest.mock import Mock, patch
from django.utils import timezone
import pyarrow
from cjwkernel.chroot import (
    EDITABLE_CHROOT,
    ensure_initialized as ensure_chroot_initialized,
)
from cjwkernel.errors import ModuleExitedError
from cjwkernel.types import I18nMessage, RenderError, RenderResult, Tab
from cjwkernel.tests.util import (
    arrow_table,
    arrow_table_context,
    parquet_file,
    assert_arrow_table_equals,
)
from cjwstate import minio, rendercache
from cjwstate.storedobjects import create_stored_object
from cjwstate.models import ModuleVersion, Workflow
from cjwstate.modules.loaded_module import LoadedModule
from cjwstate.tests.utils import DbTestCase
from renderer import notifications
from renderer.execute.wf_module import execute_wfmodule


async def noop(*args, **kwargs):
    return


class WfModuleTests(DbTestCase):
    @classmethod
    def setUpClass(cls):
        ensure_chroot_initialized()

    def setUp(self):
        super().setUp()
        self.ctx = contextlib.ExitStack()
        self.chroot_context = self.ctx.enter_context(EDITABLE_CHROOT.acquire_context())
        basedir = self.ctx.enter_context(
            self.chroot_context.tempdir_context(prefix="test_wf_module-")
        )
        self.output_path = self.ctx.enter_context(
            self.chroot_context.tempfile_context(prefix="output-", dir=basedir)
        )

    def tearDown(self):
        self.ctx.close()
        super().tearDown()

    @contextlib.contextmanager
    def _stub_module(self, render_fn):
        mock_module = Mock(LoadedModule)
        mock_module.render.side_effect = render_fn
        ModuleVersion.create_or_replace_from_spec(
            {"id_name": "x", "name": "X", "category": "Clean", "parameters": []}
        )
        with patch.object(LoadedModule, "for_module_version", lambda *a: mock_module):
            yield

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
                self.chroot_context,
                workflow,
                wf_module,
                {},
                tab.to_arrow(),
                RenderResult(),
                {},
                self.output_path,
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

    @patch("server.websockets.ws_client_send_delta_async", noop)
    @patch.object(notifications, "email_output_delta")
    def test_email_delta(self, email_delta):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wf_module = tab.wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id - 1,
            notifications=True,
        )
        rendercache.cache_render_result(
            workflow,
            wf_module,
            workflow.last_delta_id - 1,
            RenderResult(arrow_table({"A": [1]})),
        )
        wf_module.last_relevant_delta_id = workflow.last_delta_id
        wf_module.save(update_fields=["last_relevant_delta_id"])

        with arrow_table_context({"A": [2]}) as table2:

            def render(*args, **kwargs):
                return RenderResult(table2)

            with self._stub_module(render):
                self.run_with_async_db(
                    execute_wfmodule(
                        self.chroot_context,
                        workflow,
                        wf_module,
                        {},
                        Tab(tab.slug, tab.name),
                        RenderResult(),
                        {},
                        self.output_path,
                    )
                )

        email_delta.assert_called()
        delta = email_delta.call_args[0][0]
        self.assertEqual(delta.user, workflow.owner)
        self.assertEqual(delta.workflow, workflow)
        self.assertEqual(delta.wf_module, wf_module)
        self.assertEqual(delta.old_result, RenderResult(arrow_table({"A": [1]})))
        self.assertEqual(delta.new_result, RenderResult(arrow_table({"A": [2]})))

    @patch("server.websockets.ws_client_send_delta_async", noop)
    @patch.object(rendercache, "open_cached_render_result")
    @patch.object(notifications, "email_output_delta")
    def test_email_delta_ignore_corrupt_cache_error(self, email_delta, read_cache):
        read_cache.side_effect = rendercache.CorruptCacheError
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wf_module = tab.wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id - 1,
            notifications=True,
        )
        # We need to actually populate the cache to set up the test. The code
        # under test will only try to open the render result if the database
        # says there's something there.
        rendercache.cache_render_result(
            workflow,
            wf_module,
            workflow.last_delta_id - 1,
            RenderResult(arrow_table({"A": [1]})),
        )
        wf_module.last_relevant_delta_id = workflow.last_delta_id
        wf_module.save(update_fields=["last_relevant_delta_id"])

        with arrow_table_context({"A": [2]}) as table2:

            def render(*args, **kwargs):
                return RenderResult(table2)

            with self._stub_module(render):
                with self.assertLogs(level=logging.ERROR):
                    self.run_with_async_db(
                        execute_wfmodule(
                            self.chroot_context,
                            workflow,
                            wf_module,
                            {},
                            Tab(tab.slug, tab.name),
                            RenderResult(),
                            {},
                            self.output_path,
                        )
                    )

        email_delta.assert_not_called()

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
            so = create_stored_object(workflow.id, wf_module.id, path)
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
                    self.chroot_context,
                    workflow,
                    wf_module,
                    {},
                    Tab(tab.slug, tab.name),
                    RenderResult(),
                    {},
                    self.output_path,
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
            so = create_stored_object(workflow.id, wf_module.id, path)
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
                    self.chroot_context,
                    workflow,
                    wf_module,
                    {},
                    Tab(tab.slug, tab.name),
                    RenderResult(),
                    {},
                    self.output_path,
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
                    self.chroot_context,
                    workflow,
                    wf_module,
                    {},
                    Tab(tab.slug, tab.name),
                    RenderResult(),
                    {},
                    self.output_path,
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
                    self.chroot_context,
                    workflow,
                    wf_module,
                    {},
                    Tab(tab.slug, tab.name),
                    RenderResult(),
                    {},
                    self.output_path,
                )
            )

    @patch("server.websockets.ws_client_send_delta_async", noop)
    def test_fetch_result_no_bucket_or_key_stored_object_means_none(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wf_module = tab.wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id,
            stored_data_version=timezone.now(),
        )
        wf_module.stored_objects.create(
            stored_at=wf_module.stored_data_version,
            bucket="",
            key="",
            size=0,
            hash="whatever",
        )

        def render(*args, fetch_result, **kwargs):
            self.assertIsNone(fetch_result)
            return RenderResult()

        with self._stub_module(render):
            self.run_with_async_db(
                execute_wfmodule(
                    self.chroot_context,
                    workflow,
                    wf_module,
                    {},
                    Tab(tab.slug, tab.name),
                    RenderResult(),
                    {},
                    self.output_path,
                )
            )

    @patch("server.websockets.ws_client_send_delta_async", noop)
    def test_report_module_error(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wf_module = tab.wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id,
        )

        def render(*args, fetch_result, **kwargs):
            raise ModuleExitedError(-9, "")

        with self._stub_module(render):
            result = self.run_with_async_db(
                execute_wfmodule(
                    self.chroot_context,
                    workflow,
                    wf_module,
                    {},
                    Tab(tab.slug, tab.name),
                    RenderResult(),
                    {},
                    self.output_path,
                )
            )
        self.assertEqual(
            result,
            RenderResult(
                errors=[
                    RenderError(
                        I18nMessage.TODO_i18n(
                            "Something unexpected happened. We have been notified and are "
                            "working to fix it. If this persists, contact us. Error code: "
                            "SIGKILL"
                        )
                    )
                ]
            ),
        )
