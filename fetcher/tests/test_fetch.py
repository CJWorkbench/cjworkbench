import contextlib
from dataclasses import dataclass, field
from functools import partial
import logging
from pathlib import Path
import unittest
from unittest.mock import patch
from dateutil import parser
from django.utils import timezone
import pyarrow.parquet
from cjwkernel.chroot import EDITABLE_CHROOT
from cjwkernel.errors import ModuleExitedError
from cjwkernel.param_dtype import ParamDType
from cjwkernel.types import (
    Column,
    ColumnType,
    FetchResult,
    I18nMessage,
    Params,
    RenderError,
    RenderResult,
    TableMetadata,
)
from cjwkernel.util import tempdir_context, tempfile_context
from cjwkernel.tests.util import (
    arrow_table_context,
    assert_arrow_table_equals,
    parquet_file,
)
from cjwstate import minio, rendercache, storedobjects
from cjwstate.models import CachedRenderResult, ModuleVersion, WfModule, Workflow
import cjwstate.modules
from cjwstate.modules.loaded_module import LoadedModule
from cjwstate.tests.utils import DbTestCase
from fetcher import fetch, fetchprep, save
from server import websockets


def async_value(v):
    async def async_value_inner(*args, **kwargs):
        return v

    return async_value_inner


@dataclass(frozen=True)
class MockModuleVersion:
    id_name: str = "mod"
    source_version_hash: str = "abc123"
    param_schema: ParamDType.Dict = field(default_factory=partial(ParamDType.Dict, {}))


class LoadDatabaseObjectsTests(DbTestCase):
    def test_load_simple(self):
        workflow = Workflow.create_and_init()
        module_version = ModuleVersion.create_or_replace_from_spec(
            {"id_name": "foo", "name": "Foo", "category": "Clean", "parameters": []}
        )
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, slug="step-1", module_id_name="foo"
        )
        result = self.run_with_async_db(
            fetch.load_database_objects(workflow.id, wf_module.id)
        )
        self.assertEqual(result[0], wf_module)
        self.assertEqual(result.wf_module, wf_module)
        self.assertEqual(result[1], module_version)
        self.assertEqual(result.module_version, module_version)
        self.assertIsNone(result[2])
        self.assertIsNone(result[3])

    def test_load_deleted_wf_module_raises(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, slug="step-1", is_deleted=True
        )
        with self.assertRaises(WfModule.DoesNotExist):
            self.run_with_async_db(
                fetch.load_database_objects(workflow.id, wf_module.id)
            )

    def test_load_deleted_tab_raises(self):
        workflow = Workflow.create_and_init()
        tab2 = workflow.tabs.create(position=1, is_deleted=True)
        wf_module = tab2.wf_modules.create(order=0, slug="step-1")
        with self.assertRaises(WfModule.DoesNotExist):
            self.run_with_async_db(
                fetch.load_database_objects(workflow.id, wf_module.id)
            )

    def test_load_deleted_workflow_raises(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(order=0, slug="step-1")
        with self.assertRaises(Workflow.DoesNotExist):
            self.run_with_async_db(
                fetch.load_database_objects(workflow.id + 1, wf_module.id)
            )

    def test_load_deleted_module_version_is_none(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, slug="step-1", module_id_name="foodeleted"
        )
        result = self.run_with_async_db(
            fetch.load_database_objects(workflow.id, wf_module.id)
        )
        self.assertIsNone(result.module_version)

    def test_load_selected_stored_object(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, slug="step-1", module_id_name="foodeleted"
        )
        with parquet_file({"A": [1]}) as path1:
            storedobjects.create_stored_object(workflow.id, wf_module.id, path1)
        with parquet_file({"A": [2]}) as path2:
            so2 = storedobjects.create_stored_object(workflow.id, wf_module.id, path2)
        with parquet_file({"A": [3]}) as path3:
            storedobjects.create_stored_object(workflow.id, wf_module.id, path3)
        wf_module.stored_data_version = so2.stored_at
        wf_module.save(update_fields=["stored_data_version"])
        result = self.run_with_async_db(
            fetch.load_database_objects(workflow.id, wf_module.id)
        )
        self.assertEqual(result[2], so2)
        self.assertEqual(result.stored_object, so2)

    def test_load_input_cached_render_result(self):
        with arrow_table_context({"A": [1]}) as atable:
            input_render_result = RenderResult(atable)

            workflow = Workflow.create_and_init()
            step1 = workflow.tabs.first().wf_modules.create(
                order=0, slug="step-1", last_relevant_delta_id=workflow.last_delta_id
            )
            step2 = workflow.tabs.first().wf_modules.create(order=1, slug="step-2")
            rendercache.cache_render_result(
                workflow, step1, workflow.last_delta_id, input_render_result
            )
            result = self.run_with_async_db(
                fetch.load_database_objects(workflow.id, step2.id)
            )
            input_crr = step1.cached_render_result
            assert input_crr is not None
            self.assertEqual(result[3], input_crr)
            self.assertEqual(result.input_cached_render_result, input_crr)

    def test_load_input_cached_render_result_is_none(self):
        # Most of these tests assume the fetch is at step 0. This one tests
        # step 1, when step 2 has no cached render result.
        workflow = Workflow.create_and_init()
        workflow.tabs.first().wf_modules.create(
            order=0, slug="step-1", last_relevant_delta_id=workflow.last_delta_id
        )
        step2 = workflow.tabs.first().wf_modules.create(order=1, slug="step-2")
        result = self.run_with_async_db(
            fetch.load_database_objects(workflow.id, step2.id)
        )
        self.assertEqual(result.input_cached_render_result, None)


class FetchOrWrapErrorTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.ctx = contextlib.ExitStack()
        self.chroot_context = self.ctx.enter_context(EDITABLE_CHROOT.acquire_context())
        self.basedir = self.ctx.enter_context(self.chroot_context.tempdir_context())
        self.output_path = self.ctx.enter_context(
            self.chroot_context.tempfile_context(dir=self.basedir)
        )

    def tearDown(self):
        self.ctx.close()
        super().tearDown()

    def _err(self, message: str) -> FetchResult:
        return FetchResult(
            self.output_path, [RenderError(I18nMessage.TODO_i18n(message))]
        )

    def _bug_err(self, message: str) -> FetchResult:
        return self._err(
            "Something unexpected happened. We have been notified and are "
            "working to fix it. If this persists, contact us. Error code: " + message
        )

    def test_deleted_wf_module(self):
        with self.assertLogs(level=logging.INFO):
            result = fetch.fetch_or_wrap_error(
                self.ctx,
                self.chroot_context,
                self.basedir,
                WfModule(),
                None,
                {},
                None,
                None,
                self.output_path,
            )
        self.assertEqual(self.output_path.stat().st_size, 0)
        self.assertEqual(result, self._err("Cannot fetch: module was deleted"))

    @patch.object(LoadedModule, "for_module_version")
    def test_load_module_missing(self, load_module):
        load_module.side_effect = FileNotFoundError
        with self.assertLogs(level=logging.INFO):
            result = fetch.fetch_or_wrap_error(
                self.ctx,
                self.chroot_context,
                self.basedir,
                WfModule(),
                MockModuleVersion("missing"),
                {},
                None,
                None,
                self.output_path,
            )
        self.assertEqual(self.output_path.stat().st_size, 0)
        self.assertEqual(result, self._bug_err("FileNotFoundError"))

    @patch.object(LoadedModule, "for_module_version")
    def test_load_module_compile_error(self, load_module):
        load_module.side_effect = ModuleExitedError(1, "log")
        with self.assertLogs(level=logging.ERROR):
            result = fetch.fetch_or_wrap_error(
                self.ctx,
                self.chroot_context,
                self.basedir,
                WfModule(),
                MockModuleVersion("bad"),
                {},
                None,
                None,
                self.output_path,
            )
        self.assertEqual(self.output_path.stat().st_size, 0)
        self.assertEqual(result, self._bug_err("exit code 1: log (during load)"))

    @patch.object(LoadedModule, "for_module_version")
    def test_simple(self, load_module):
        load_module.return_value.migrate_params.return_value = {"A": "B"}
        load_module.return_value.fetch.return_value = FetchResult(self.output_path, [])
        result = fetch.fetch_or_wrap_error(
            self.ctx,
            self.chroot_context,
            self.basedir,
            WfModule(params={"A": "input"}, secrets={"C": "wrong"}),
            MockModuleVersion(
                id_name="A", param_schema=ParamDType.Dict({"A": ParamDType.String()})
            ),
            {"C": "D"},
            None,
            None,
            self.output_path,
        )
        self.assertEqual(result, FetchResult(self.output_path, []))
        load_module.return_value.migrate_params.assert_called_with({"A": "input"})
        load_module.return_value.fetch.assert_called_with(
            chroot_context=self.chroot_context,
            basedir=self.basedir,
            params=Params({"A": "B"}),
            secrets={"C": "D"},
            last_fetch_result=None,
            input_parquet_filename=None,
            output_filename=self.output_path.name,
        )

    @patch.object(LoadedModule, "for_module_version")
    @patch.object(fetchprep, "clean_value")
    @patch.object(rendercache, "downloaded_parquet_file")
    def test_input_crr(self, downloaded_parquet_file, clean_value, load_module):
        load_module.return_value.migrate_params.return_value = {}
        load_module.return_value.fetch.return_value = FetchResult(self.output_path, [])
        clean_value.return_value = {}
        downloaded_parquet_file.return_value = Path("/path/to/x.parquet")
        input_metadata = TableMetadata(3, [Column("A", ColumnType.Text())])
        input_crr = CachedRenderResult(1, 2, 3, "ok", [], {}, input_metadata)
        fetch.fetch_or_wrap_error(
            self.ctx,
            self.chroot_context,
            self.basedir,
            WfModule(),
            MockModuleVersion(),
            {},
            None,
            input_crr,
            self.output_path,
        )
        # Passed file is downloaded from rendercache
        downloaded_parquet_file.assert_called_with(input_crr, dir=self.basedir)
        self.assertEqual(
            load_module.return_value.fetch.call_args[1]["input_parquet_filename"],
            "x.parquet",
        )
        # clean_value() is called with input metadata from CachedRenderResult
        clean_value.assert_called()
        self.assertEqual(clean_value.call_args[0][2], input_metadata)

    @patch.object(LoadedModule, "for_module_version")
    @patch.object(fetchprep, "clean_value", lambda *a: {})
    @patch.object(rendercache, "downloaded_parquet_file")
    def test_input_crr_corrupt_cache_error_is_none(
        self, downloaded_parquet_file, load_module
    ):
        load_module.return_value.migrate_params.return_value = {}
        load_module.return_value.fetch.return_value = FetchResult(self.output_path, [])
        downloaded_parquet_file.side_effect = rendercache.CorruptCacheError(
            "file not found"
        )
        input_metadata = TableMetadata(3, [Column("A", ColumnType.Text())])
        input_crr = CachedRenderResult(1, 2, 3, "ok", [], {}, input_metadata)
        fetch.fetch_or_wrap_error(
            self.ctx,
            self.chroot_context,
            self.basedir,
            WfModule(),
            MockModuleVersion(),
            {},
            None,
            input_crr,
            self.output_path,
        )
        # fetch is still called, with `None` as argument.
        self.assertIsNone(
            load_module.return_value.fetch.call_args[1]["input_parquet_filename"]
        )

    @patch.object(LoadedModule, "for_module_version")
    @patch.object(fetchprep, "clean_value", lambda *a: {})
    @patch.object(storedobjects, "downloaded_file")
    def test_pass_last_fetch_result(self, downloaded_file, load_module):
        last_result_path = self.ctx.enter_context(
            tempfile_context(prefix="last-result")
        )
        result_path = self.ctx.enter_context(tempfile_context(prefix="result"))

        load_module.return_value.migrate_params.return_value = {}
        load_module.return_value.fetch.return_value = FetchResult(result_path, [])
        fetch.fetch_or_wrap_error(
            self.ctx,
            self.chroot_context,
            self.basedir,
            WfModule(fetch_error=""),
            MockModuleVersion(),
            {},
            FetchResult(last_result_path, []),
            None,
            self.output_path,
        )
        self.assertEqual(
            load_module.return_value.fetch.call_args[1]["last_fetch_result"],
            FetchResult(last_result_path, []),
        )

    @patch.object(LoadedModule, "for_module_version")
    @patch.object(fetchprep, "clean_value", lambda *a: {})
    def test_fetch_module_error(self, load_module):
        load_module.return_value.migrate_params.return_value = {}
        load_module.return_value.fetch.side_effect = ModuleExitedError(1, "bad")
        with self.assertLogs(level=logging.ERROR):
            result = fetch.fetch_or_wrap_error(
                self.ctx,
                self.chroot_context,
                self.basedir,
                WfModule(),
                MockModuleVersion(),
                {},
                None,
                None,
                self.output_path,
            )
        self.assertEqual(result, self._bug_err("exit code 1: bad"))


class FetchTests(DbTestCase):
    @patch.object(websockets, "queue_render_if_listening")
    @patch.object(websockets, "ws_client_send_delta_async")
    def test_fetch_integration(self, send_delta, queue_render):
        queue_render.side_effect = async_value(None)
        send_delta.side_effect = async_value(None)
        workflow = Workflow.create_and_init()
        ModuleVersion.create_or_replace_from_spec(
            {"id_name": "mod", "name": "Mod", "category": "Clean", "parameters": []},
            source_version_hash="abc123",
        )
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, slug="step-1", module_id_name="mod"
        )
        minio.put_bytes(
            minio.ExternalModulesBucket,
            "mod/abc123/code.py",
            b"import pandas as pd\ndef fetch(params): return pd.DataFrame({'A': [1]})\ndef render(table, params): return table",
        )
        cjwstate.modules.init_module_system()
        now = timezone.now()
        with self.assertLogs(level=logging.INFO):
            self.run_with_async_db(
                fetch.fetch(workflow_id=workflow.id, wf_module_id=wf_module.id, now=now)
            )
        wf_module.refresh_from_db()
        so = wf_module.stored_objects.get(stored_at=wf_module.stored_data_version)
        with minio.temporarily_download(so.bucket, so.key) as parquet_path:
            table = pyarrow.parquet.read_table(str(parquet_path), use_threads=False)
            assert_arrow_table_equals(table, {"A": [1]})

        workflow.refresh_from_db()
        queue_render.assert_called_with(workflow.id, workflow.last_delta_id)
        send_delta.assert_called()

    @patch.object(save, "create_result")
    def test_fetch_integration_tempfiles_are_on_disk(self, create_result):
        # /tmp is RAM; /var/tmp is disk. Assert big files go on disk.
        workflow = Workflow.create_and_init()
        ModuleVersion.create_or_replace_from_spec(
            {"id_name": "mod", "name": "Mod", "category": "Clean", "parameters": []},
            source_version_hash="abc123",
        )
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, slug="step-1", module_id_name="mod"
        )
        minio.put_bytes(
            minio.ExternalModulesBucket,
            "mod/abc123/code.py",
            b"import pandas as pd\ndef fetch(params): return pd.DataFrame({'A': [1]})\ndef render(table, params): return table",
        )
        with self.assertLogs(level=logging.INFO):
            cjwstate.modules.init_module_system()
            self.run_with_async_db(
                fetch.fetch(workflow_id=workflow.id, wf_module_id=wf_module.id)
            )
        create_result.assert_called()
        saved_result: FetchResult = create_result.call_args[0][2]
        self.assertRegex(str(saved_result.path), r"/var/tmp/")


class UpdateNextUpdateTimeTests(DbTestCase):
    def test_update_on_schedule(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            slug="step-1",
            auto_update_data=True,
            update_interval=3600,
            next_update=parser.parse("2000-01-01T01:00Z"),
        )
        self.run_with_async_db(
            fetch.update_next_update_time(
                workflow.id, wf_module, parser.parse("2001-01-01T01:00:01Z")
            )
        )
        wf_module.refresh_from_db()
        self.assertEqual(
            wf_module.last_update_check, parser.parse("2001-01-01T01:00:01Z")
        )
        self.assertEqual(wf_module.next_update, parser.parse("2001-01-01T02:00Z"))

    def test_update_skip_missed_updates(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            slug="step-1",
            auto_update_data=True,
            update_interval=3600,
            next_update=parser.parse("2000-01-01T01:00Z"),
        )
        self.run_with_async_db(
            fetch.update_next_update_time(
                workflow.id, wf_module, parser.parse("2001-01-01T03:59Z")
            )
        )
        wf_module.refresh_from_db()
        self.assertEqual(wf_module.next_update, parser.parse("2001-01-01T04:00Z"))

    def test_update_race_auto_update_disabled(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            slug="step-1",
            auto_update_data=False,
            update_interval=3600,
            next_update=None,
        )
        self.run_with_async_db(
            fetch.update_next_update_time(
                workflow.id, wf_module, parser.parse("2001-01-01T02:59Z")
            )
        )
        wf_module.refresh_from_db()
        self.assertIsNone(wf_module.next_update)

    def test_update_race_wf_module_deleted(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            slug="step-1",
            auto_update_data=True,
            update_interval=3600,
            next_update=parser.parse("2000-01-01T01:00Z"),
        )
        WfModule.objects.filter(id=wf_module.id).delete()
        # does not crash
        self.run_with_async_db(
            fetch.update_next_update_time(
                workflow.id, wf_module, parser.parse("2001-01-01T02:59Z")
            )
        )

    def test_update_race_workflow_deleted(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            slug="step-1",
            auto_update_data=True,
            update_interval=3600,
            next_update=parser.parse("2000-01-01T01:00Z"),
        )
        workflow.delete()
        # does not crash
        self.run_with_async_db(
            fetch.update_next_update_time(
                workflow.id, wf_module, parser.parse("2001-01-01T02:59Z")
            )
        )
