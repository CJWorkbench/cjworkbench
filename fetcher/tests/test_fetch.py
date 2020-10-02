import contextlib
from dataclasses import dataclass, field
from functools import partial
import logging
from pathlib import Path
import shutil
import textwrap
import unittest
from unittest.mock import patch
from dateutil import parser
from django.utils import timezone
import pyarrow.parquet
from cjwkernel.chroot import EDITABLE_CHROOT
from cjwkernel.errors import ModuleExitedError
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
from cjwkernel.util import tempfile_context
from cjwkernel.tests.util import (
    arrow_table_context,
    assert_arrow_table_equals,
    parquet_file,
)
from cjwstate import minio, rabbitmq, rendercache, storedobjects
from cjwstate.models import CachedRenderResult, ModuleVersion, Step, Workflow
import cjwstate.modules
from cjwstate.modules.param_dtype import ParamDType
from cjwstate.tests.utils import (
    DbTestCase,
    DbTestCaseWithModuleRegistry,
    DbTestCaseWithModuleRegistryAndMockKernel,
    create_module_zipfile,
)
from fetcher import fetch, fetchprep, save


def async_value(v):
    async def async_value_inner(*args, **kwargs):
        return v

    return async_value_inner


@dataclass(frozen=True)
class MockModuleVersion:
    id_name: str = "mod"
    source_version_hash: str = "abc123"
    param_schema: ParamDType.Dict = field(default_factory=partial(ParamDType.Dict, {}))


class LoadDatabaseObjectsTests(DbTestCaseWithModuleRegistry):
    def test_load_simple(self):
        workflow = Workflow.create_and_init()
        module_zipfile = create_module_zipfile("foo")
        step = workflow.tabs.first().steps.create(
            order=0, slug="step-1", module_id_name="foo"
        )
        with self.assertLogs("cjwstate.params", level=logging.INFO):
            result = self.run_with_async_db(
                fetch.load_database_objects(workflow.id, step.id)
            )
        self.assertEqual(result.step, step)
        self.assertEqual(result.module_zipfile, module_zipfile)
        self.assertEqual(result.migrated_params_or_error, {})
        self.assertIsNone(result.stored_object)
        self.assertIsNone(result.input_cached_render_result)

    def test_load_deleted_step_raises(self):
        workflow = Workflow.create_and_init()
        step = workflow.tabs.first().steps.create(
            order=0, slug="step-1", is_deleted=True
        )
        with self.assertRaises(Step.DoesNotExist):
            self.run_with_async_db(fetch.load_database_objects(workflow.id, step.id))

    def test_load_deleted_tab_raises(self):
        workflow = Workflow.create_and_init()
        tab2 = workflow.tabs.create(position=1, is_deleted=True)
        step = tab2.steps.create(order=0, slug="step-1")
        with self.assertRaises(Step.DoesNotExist):
            self.run_with_async_db(fetch.load_database_objects(workflow.id, step.id))

    def test_load_deleted_workflow_raises(self):
        workflow = Workflow.create_and_init()
        step = workflow.tabs.first().steps.create(order=0, slug="step-1")
        with self.assertRaises(Workflow.DoesNotExist):
            self.run_with_async_db(
                fetch.load_database_objects(workflow.id + 1, step.id)
            )

    def test_load_migrate_params_even_when_invalid(self):
        workflow = Workflow.create_and_init()
        module_zipfile = create_module_zipfile(
            "mod",
            spec_kwargs={"parameters": [{"id_name": "a", "type": "string"}]},
            python_code=textwrap.dedent(
                """
                def migrate_params(params):
                    return {"x": "y"}  # does not validate
                """
            ),
        )
        step = workflow.tabs.first().steps.create(
            order=0, slug="step-1", module_id_name="mod", params={"a": "b"}
        )
        with self.assertLogs("cjwstate.params", level=logging.INFO):
            result = self.run_with_async_db(
                fetch.load_database_objects(workflow.id, step.id)
            )
        self.assertEqual(result.migrated_params_or_error, {"x": "y"})

    def test_load_migrate_params_raise_module_error(self):
        workflow = Workflow.create_and_init()
        module_zipfile = create_module_zipfile(
            "mod",
            spec_kwargs={"parameters": [{"id_name": "a", "type": "string"}]},
            python_code=textwrap.dedent(
                """
                def migrate_params(params):
                    raise RuntimeError("bad")
                """
            ),
        )
        step = workflow.tabs.first().steps.create(
            order=0, slug="step-1", module_id_name="mod", params={"a": "b"}
        )
        with self.assertLogs("cjwstate.params", level=logging.INFO):
            result = self.run_with_async_db(
                fetch.load_database_objects(workflow.id, step.id)
            )
        self.assertIsInstance(result.migrated_params_or_error, ModuleExitedError)
        self.assertRegex(result.migrated_params_or_error.log, ".*RuntimeError: bad")

    def test_load_deleted_module_version_is_none(self):
        workflow = Workflow.create_and_init()
        step = workflow.tabs.first().steps.create(
            order=0, slug="step-1", module_id_name="foodeleted", params={"a": "b"}
        )
        result = self.run_with_async_db(
            fetch.load_database_objects(workflow.id, step.id)
        )
        self.assertIsNone(result.module_zipfile)
        self.assertEqual(result.migrated_params_or_error, {})

    def test_load_selected_stored_object(self):
        workflow = Workflow.create_and_init()
        step = workflow.tabs.first().steps.create(
            order=0, slug="step-1", module_id_name="foodeleted"
        )
        with parquet_file({"A": [1]}) as path1:
            storedobjects.create_stored_object(workflow.id, step.id, path1)
        with parquet_file({"A": [2]}) as path2:
            so2 = storedobjects.create_stored_object(workflow.id, step.id, path2)
        with parquet_file({"A": [3]}) as path3:
            storedobjects.create_stored_object(workflow.id, step.id, path3)
        step.stored_data_version = so2.stored_at
        step.save(update_fields=["stored_data_version"])
        result = self.run_with_async_db(
            fetch.load_database_objects(workflow.id, step.id)
        )
        self.assertEqual(result[3], so2)
        self.assertEqual(result.stored_object, so2)

    def test_load_input_cached_render_result(self):
        with arrow_table_context({"A": [1]}) as atable:
            input_render_result = RenderResult(atable)

            workflow = Workflow.create_and_init()
            step1 = workflow.tabs.first().steps.create(
                order=0, slug="step-1", last_relevant_delta_id=workflow.last_delta_id
            )
            step2 = workflow.tabs.first().steps.create(order=1, slug="step-2")
            rendercache.cache_render_result(
                workflow, step1, workflow.last_delta_id, input_render_result
            )
            result = self.run_with_async_db(
                fetch.load_database_objects(workflow.id, step2.id)
            )
            input_crr = step1.cached_render_result
            assert input_crr is not None
            self.assertEqual(result[4], input_crr)
            self.assertEqual(result.input_cached_render_result, input_crr)

    def test_load_input_cached_render_result_is_none(self):
        # Most of these tests assume the fetch is at step 0. This one tests
        # step 1, when step 2 has no cached render result.
        workflow = Workflow.create_and_init()
        workflow.tabs.first().steps.create(
            order=0, slug="step-1", last_relevant_delta_id=workflow.last_delta_id
        )
        step2 = workflow.tabs.first().steps.create(order=1, slug="step-2")
        result = self.run_with_async_db(
            fetch.load_database_objects(workflow.id, step2.id)
        )
        self.assertEqual(result.input_cached_render_result, None)


class FetchOrWrapErrorTests(DbTestCaseWithModuleRegistryAndMockKernel):
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

    def _err(self, message: I18nMessage) -> FetchResult:
        return FetchResult(self.output_path, [RenderError(message)])

    def _bug_err(self, message: str) -> FetchResult:
        return self._err(
            I18nMessage(
                "py.fetcher.fetch.user_visible_bug_during_fetch", {"message": message}
            )
        )

    def test_deleted_step(self):
        with self.assertLogs(level=logging.INFO):
            result = fetch.fetch_or_wrap_error(
                self.ctx,
                self.chroot_context,
                self.basedir,
                "mod",
                None,
                {},
                {},
                None,
                None,
                self.output_path,
            )
        self.assertEqual(self.output_path.stat().st_size, 0)
        self.assertEqual(
            result, self._err(I18nMessage("py.fetcher.fetch.no_loaded_module"))
        )

    def test_simple(self):
        self.kernel.fetch.return_value = FetchResult(self.output_path)
        module_zipfile = create_module_zipfile(
            "mod", spec_kwargs={"parameters": [{"id_name": "A", "type": "string"}]}
        )
        with self.assertLogs("fetcher.fetch", level=logging.INFO):
            result = fetch.fetch_or_wrap_error(
                self.ctx,
                self.chroot_context,
                self.basedir,
                "mod",
                module_zipfile,
                {"A": "B"},
                {"C": "D"},
                None,
                None,
                self.output_path,
            )
        self.assertEqual(result, FetchResult(self.output_path, []))
        self.assertEqual(
            self.kernel.fetch.call_args[1]["compiled_module"],
            module_zipfile.compile_code_without_executing(),
        )
        self.assertEqual(self.kernel.fetch.call_args[1]["params"], Params({"A": "B"}))
        self.assertEqual(self.kernel.fetch.call_args[1]["secrets"], {"C": "D"})
        self.assertIsNone(self.kernel.fetch.call_args[1]["last_fetch_result"])
        self.assertIsNone(self.kernel.fetch.call_args[1]["input_parquet_filename"])

    def test_migrated_params_is_error(self):
        with self.assertLogs("fetcher.fetch", level=logging.ERROR):
            result = fetch.fetch_or_wrap_error(
                self.ctx,
                self.chroot_context,
                self.basedir,
                "mod",
                create_module_zipfile("mod"),
                ModuleExitedError(1, "Traceback:\n\n\nRuntimeError: bad"),
                {},
                None,
                None,
                self.output_path,
            )
        self.assertEqual(result, self._bug_err("exit code 1: RuntimeError: bad"))

    def test_migrated_params_is_invalid(self):
        module_zipfile = create_module_zipfile(
            "mod", spec_kwargs={"parameters": [{"id_name": "a", "type": "string"}]}
        )
        with self.assertLogs("fetcher.fetch", level=logging.ERROR):
            result = fetch.fetch_or_wrap_error(
                self.ctx,
                self.chroot_context,
                self.basedir,
                "mod",
                module_zipfile,
                {"a": 2},  # invalid: should be string
                {},
                None,
                None,
                self.output_path,
            )
        self.assertEqual(
            result,
            self._bug_err(
                "%s:migrate_params() output invalid params" % module_zipfile.path.name
            ),
        )

    @patch.object(fetchprep, "clean_value")
    @patch.object(rendercache, "downloaded_parquet_file")
    def test_input_crr(self, downloaded_parquet_file, clean_value):
        def do_fetch(
            compiled_module,
            chroot_context,
            basedir,
            params,
            secrets,
            last_fetch_result,
            input_parquet_filename,
            output_filename,
        ):
            shutil.copy(basedir / input_parquet_filename, basedir / output_filename)
            return FetchResult(basedir / output_filename)

        self.kernel.fetch.side_effect = do_fetch
        clean_value.return_value = {}

        with tempfile_context(dir=self.basedir, suffix=".parquet") as parquet_path:
            parquet_path.write_bytes(b"abc123")
            downloaded_parquet_file.return_value = parquet_path

            input_metadata = TableMetadata(3, [Column("A", ColumnType.Text())])
            input_crr = CachedRenderResult(1, 2, 3, "ok", [], {}, input_metadata)
            with self.assertLogs("fetcher.fetch", level=logging.INFO):
                result = fetch.fetch_or_wrap_error(
                    self.ctx,
                    self.chroot_context,
                    self.basedir,
                    "mod",
                    create_module_zipfile("mod"),
                    {},
                    {},
                    None,
                    input_crr,
                    self.output_path,
                )

            # Passed file is downloaded from rendercache
            self.assertEqual(result.path.read_bytes(), b"abc123")
            # clean_value() is called with input metadata from CachedRenderResult
            clean_value.assert_called()
            self.assertEqual(clean_value.call_args[0][2], input_metadata)

    @patch.object(fetchprep, "clean_value", lambda *a: {})
    @patch.object(rendercache, "downloaded_parquet_file")
    def test_input_crr_corrupt_cache_error_is_none(self, downloaded_parquet_file):
        self.kernel.fetch.return_value = FetchResult(self.output_path, [])
        downloaded_parquet_file.side_effect = rendercache.CorruptCacheError(
            "file not found"
        )
        input_metadata = TableMetadata(3, [Column("A", ColumnType.Text())])
        input_crr = CachedRenderResult(1, 2, 3, "ok", [], {}, input_metadata)
        with self.assertLogs("fetcher.fetch", level=logging.INFO):
            fetch.fetch_or_wrap_error(
                self.ctx,
                self.chroot_context,
                self.basedir,
                "mod",
                create_module_zipfile("mod"),
                {},
                {},
                None,
                input_crr,
                self.output_path,
            )
        # fetch is still called, with `None` as argument.
        self.assertIsNone(self.kernel.fetch.call_args[1]["input_parquet_filename"])

    @patch.object(storedobjects, "downloaded_file")
    def test_pass_last_fetch_result(self, downloaded_file):
        last_result_path = self.ctx.enter_context(
            tempfile_context(prefix="last-result")
        )

        result_path = self.ctx.enter_context(tempfile_context(prefix="result"))

        self.kernel.fetch.return_value = FetchResult(result_path, [])
        with self.assertLogs("fetcher.fetch", level=logging.INFO):
            fetch.fetch_or_wrap_error(
                self.ctx,
                self.chroot_context,
                self.basedir,
                "mod",
                create_module_zipfile("mod"),
                {},
                {},
                FetchResult(last_result_path, []),
                None,
                self.output_path,
            )
        self.assertEqual(
            self.kernel.fetch.call_args[1]["last_fetch_result"],
            FetchResult(last_result_path, []),
        )

    def test_fetch_module_error(self):
        self.kernel.fetch.side_effect = ModuleExitedError(1, "RuntimeError: bad")
        with self.assertLogs(level=logging.ERROR):
            result = fetch.fetch_or_wrap_error(
                self.ctx,
                self.chroot_context,
                self.basedir,
                "mod",
                create_module_zipfile("mod"),
                {},
                {},
                None,
                None,
                self.output_path,
            )
        self.assertEqual(result, self._bug_err("exit code 1: RuntimeError: bad"))


class FetchTests(DbTestCaseWithModuleRegistry):
    @patch.object(rabbitmq, "queue_render_if_consumers_are_listening")
    @patch.object(rabbitmq, "send_update_to_workflow_clients")
    def test_fetch_integration(self, send_update, queue_render):
        queue_render.side_effect = async_value(None)
        send_update.side_effect = async_value(None)
        workflow = Workflow.create_and_init()
        create_module_zipfile(
            "mod",
            python_code=(
                "import pandas as pd\ndef fetch(params): return pd.DataFrame({'A': [1]})\ndef render(table, params): return table"
            ),
        )
        step = workflow.tabs.first().steps.create(
            order=0, slug="step-1", module_id_name="mod"
        )
        cjwstate.modules.init_module_system()
        now = timezone.now()
        with self.assertLogs(level=logging.INFO):
            self.run_with_async_db(
                fetch.fetch(workflow_id=workflow.id, step_id=step.id, now=now)
            )
        step.refresh_from_db()
        so = step.stored_objects.get(stored_at=step.stored_data_version)
        with minio.temporarily_download(
            minio.StoredObjectsBucket, so.key
        ) as parquet_path:
            table = pyarrow.parquet.read_table(str(parquet_path), use_threads=False)
            assert_arrow_table_equals(table, {"A": [1]})

        workflow.refresh_from_db()
        queue_render.assert_called_with(workflow.id, workflow.last_delta_id)
        send_update.assert_called()

    @patch.object(save, "create_result")
    def test_fetch_integration_tempfiles_are_on_disk(self, create_result):
        # /tmp is RAM; /var/tmp is disk. Assert big files go on disk.
        workflow = Workflow.create_and_init()
        create_module_zipfile(
            "mod",
            python_code=(
                "import pandas as pd\ndef fetch(params): return pd.DataFrame({'A': [1]})\ndef render(table, params): return table"
            ),
        )
        step = workflow.tabs.first().steps.create(
            order=0, slug="step-1", module_id_name="mod"
        )
        with self.assertLogs(level=logging.INFO):
            cjwstate.modules.init_module_system()
            self.run_with_async_db(
                fetch.fetch(workflow_id=workflow.id, step_id=step.id)
            )
        create_result.assert_called()
        saved_result: FetchResult = create_result.call_args[0][2]
        self.assertRegex(str(saved_result.path), r"/var/tmp/")


class UpdateNextUpdateTimeTests(DbTestCase):
    def test_update_on_schedule(self):
        workflow = Workflow.create_and_init()
        step = workflow.tabs.first().steps.create(
            order=0,
            slug="step-1",
            auto_update_data=True,
            update_interval=3600,
            next_update=parser.parse("2000-01-01T01:00Z"),
        )
        self.run_with_async_db(
            fetch.update_next_update_time(
                workflow.id, step, parser.parse("2001-01-01T01:00:01Z")
            )
        )
        step.refresh_from_db()
        self.assertEqual(step.last_update_check, parser.parse("2001-01-01T01:00:01Z"))
        self.assertEqual(step.next_update, parser.parse("2001-01-01T02:00Z"))

    def test_update_skip_missed_updates(self):
        workflow = Workflow.create_and_init()
        step = workflow.tabs.first().steps.create(
            order=0,
            slug="step-1",
            auto_update_data=True,
            update_interval=3600,
            next_update=parser.parse("2000-01-01T01:00Z"),
        )
        self.run_with_async_db(
            fetch.update_next_update_time(
                workflow.id, step, parser.parse("2001-01-01T03:59Z")
            )
        )
        step.refresh_from_db()
        self.assertEqual(step.next_update, parser.parse("2001-01-01T04:00Z"))

    def test_update_race_auto_update_disabled(self):
        workflow = Workflow.create_and_init()
        step = workflow.tabs.first().steps.create(
            order=0,
            slug="step-1",
            auto_update_data=False,
            update_interval=3600,
            next_update=None,
        )
        self.run_with_async_db(
            fetch.update_next_update_time(
                workflow.id, step, parser.parse("2001-01-01T02:59Z")
            )
        )
        step.refresh_from_db()
        self.assertIsNone(step.next_update)

    def test_update_race_step_deleted(self):
        workflow = Workflow.create_and_init()
        step = workflow.tabs.first().steps.create(
            order=0,
            slug="step-1",
            auto_update_data=True,
            update_interval=3600,
            next_update=parser.parse("2000-01-01T01:00Z"),
        )
        Step.objects.filter(id=step.id).delete()
        # does not crash
        self.run_with_async_db(
            fetch.update_next_update_time(
                workflow.id, step, parser.parse("2001-01-01T02:59Z")
            )
        )

    def test_update_race_workflow_deleted(self):
        workflow = Workflow.create_and_init()
        step = workflow.tabs.first().steps.create(
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
                workflow.id, step, parser.parse("2001-01-01T02:59Z")
            )
        )
