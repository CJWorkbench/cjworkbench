import contextlib
import logging
import shutil
from dataclasses import replace
from unittest.mock import patch

import pyarrow as pa
from cjwmodule.arrow.testing import assert_arrow_table_equals, make_column, make_table

from cjwkernel.chroot import EDITABLE_CHROOT
from cjwkernel.kernel import Kernel
from cjwkernel.tests.util import arrow_table_context
from cjwkernel.types import Column, ColumnType, RenderResult
from cjwkernel.validate import load_trusted_arrow_file, read_columns
from cjwstate import s3, rabbitmq, rendercache
from cjwstate.models import Workflow
from cjwstate.rendercache.testing import write_to_rendercache
from cjwstate.tests.utils import DbTestCaseWithModuleRegistry, create_module_zipfile
from renderer.execute.tab import execute_tab_flow, ExecuteStep, TabFlow
from renderer.execute.types import StepResult


async def fake_send(*args, **kwargs):
    pass


def mock_render(arrow_table: pa.Table):
    def inner(
        module_zipfile,
        *,
        chroot_context,
        basedir,
        input_filename,
        params,
        tab,
        fetch_result,
        output_filename,
    ):
        output_path = basedir / output_filename
        with arrow_table_context(arrow_table) as (table_path, table):
            shutil.copy(table_path, output_path)
            return RenderResult(errors=[])

    return inner


class TabTests(DbTestCaseWithModuleRegistry):
    @contextlib.contextmanager
    def _execute(self, workflow, flow, tab_columns, expect_log_level=logging.DEBUG):
        with EDITABLE_CHROOT.acquire_context() as chroot_context:
            with chroot_context.tempdir_context(prefix="test_tab") as tempdir:
                with chroot_context.tempfile_context(
                    prefix="execute-tab-output", suffix=".arrow", dir=tempdir
                ) as out_path:
                    with self.assertLogs("renderer.execute", level=expect_log_level):
                        result = self.run_with_async_db(
                            execute_tab_flow(
                                chroot_context, workflow, flow, tab_columns, out_path
                            )
                        )
                        yield result, out_path

    def test_execute_empty_tab(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        tab_flow = TabFlow(tab.to_arrow(), [])
        with self._execute(workflow, tab_flow, {}) as (result, path):
            self.assertEqual(result, StepResult(path, []))
            self.assertEqual(load_trusted_arrow_file(path), make_table())

    @patch.object(rabbitmq, "send_update_to_workflow_clients", fake_send)
    def test_execute_cache_hit(self):
        cached_table1 = make_table(make_column("A", [1]))
        cached_table2 = make_table(make_column("B", [2], format="${:,}"))
        module_zipfile = create_module_zipfile("mod", spec_kwargs={"loads_data": True})
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        step1 = tab.steps.create(
            order=0, slug="step-1", last_relevant_delta_id=workflow.last_delta_id
        )
        write_to_rendercache(workflow, step1, workflow.last_delta_id, cached_table1)
        step2 = tab.steps.create(
            order=1, slug="step-2", last_relevant_delta_id=workflow.last_delta_id
        )
        write_to_rendercache(workflow, step2, workflow.last_delta_id, cached_table2)

        tab_flow = TabFlow(
            tab.to_arrow(),
            [
                ExecuteStep(step1, module_zipfile, {}),
                ExecuteStep(step2, module_zipfile, {}),
            ],
        )

        unwanted_table = make_table(make_column("No", ["bad"]))
        with patch.object(Kernel, "render", side_effect=mock_render(unwanted_table)):
            with self._execute(workflow, tab_flow, {}) as (result, path):
                self.assertEqual(
                    result,
                    StepResult(path, [Column("B", ColumnType.Number(format="${:,}"))]),
                )
                assert_arrow_table_equals(load_trusted_arrow_file(path), cached_table2)

            Kernel.render.assert_not_called()

    @patch.object(rabbitmq, "send_update_to_workflow_clients", fake_send)
    def test_execute_cache_miss(self):
        module_zipfile = create_module_zipfile("mod", spec_kwargs={"loads_data": True})
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        step1 = tab.steps.create(
            order=0,
            slug="step-1",
            module_id_name="mod",
            last_relevant_delta_id=workflow.last_delta_id,
        )
        step2 = tab.steps.create(
            order=1,
            slug="step-2",
            module_id_name="mod",
            last_relevant_delta_id=workflow.last_delta_id,
        )

        tab_flow = TabFlow(
            tab.to_arrow(),
            [
                ExecuteStep(step1, module_zipfile, {}),
                ExecuteStep(step2, module_zipfile, {}),
            ],
        )

        table = make_table(make_column("A", ["a"]))

        with patch.object(Kernel, "render", side_effect=mock_render(table)):
            with self._execute(workflow, tab_flow, {}) as (result, path):
                self.assertEqual(
                    result, StepResult(path, [Column("A", ColumnType.Text())])
                )
                assert_arrow_table_equals(load_trusted_arrow_file(path), table)

            self.assertEqual(Kernel.render.call_count, 2)  # step2, not step1
            self.assertRegex(
                # Output is to the correct file
                Kernel.render.call_args[1]["output_filename"],
                r"execute-tab-output.*\.arrow",
            )

    @patch.object(rabbitmq, "send_update_to_workflow_clients", fake_send)
    def test_execute_partial_cache_hit(self):
        module_zipfile = create_module_zipfile("mod", spec_kwargs={"loads_data": True})
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        # step1: cached result is fresh. Should not render.
        step1 = tab.steps.create(
            order=0,
            slug="step-1",
            module_id_name="mod",
            last_relevant_delta_id=workflow.last_delta_id,
        )
        write_to_rendercache(
            workflow, step1, workflow.last_delta_id, make_table(make_column("A", ["a"]))
        )
        # step2: cached result is stale, so must be re-rendered
        step2 = tab.steps.create(
            order=1,
            slug="step-2",
            module_id_name="mod",
            last_relevant_delta_id=workflow.last_delta_id,
        )
        write_to_rendercache(
            workflow,
            step2,
            workflow.last_delta_id - 1,
            make_table(make_column("B", ["b"])),
        )

        tab_flow = TabFlow(
            tab.to_arrow(),
            [
                ExecuteStep(step1, module_zipfile, {}),
                ExecuteStep(step2, module_zipfile, {}),
            ],
        )

        new_table = make_table(make_column("C", ["c"]))

        with patch.object(Kernel, "render", side_effect=mock_render(new_table)):
            with self._execute(workflow, tab_flow, {}) as (result, path):
                self.assertEqual(
                    result, StepResult(path, [Column("C", ColumnType.Text())])
                )
                assert_arrow_table_equals(load_trusted_arrow_file(path), new_table)

            Kernel.render.assert_called_once()  # step2, not step1

            self.assertRegex(
                # Output is to the correct file
                Kernel.render.call_args[1]["output_filename"],
                r"execute-tab-output.*\.arrow",
            )

    @patch.object(rabbitmq, "send_update_to_workflow_clients", fake_send)
    def test_resume_backtrack_on_corrupt_cache_error(self):
        module_zipfile = create_module_zipfile("mod", spec_kwargs={"loads_data": True})
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        # step1: cached result is fresh -- but CORRUPT
        step1 = tab.steps.create(
            order=0,
            slug="step-1",
            module_id_name="mod",
            last_relevant_delta_id=workflow.last_delta_id,
        )
        write_to_rendercache(
            workflow, step1, workflow.last_delta_id, make_table(make_column("A", [1]))
        )
        step1.refresh_from_db()
        s3.put_bytes(
            # Write corrupted data -- will lead to CorruptCacheError
            rendercache.io.BUCKET,
            rendercache.io.crr_parquet_key(step1.cached_render_result),
            b"CORRUPT",
        )
        # step2: no cached result -- must re-render
        step2 = tab.steps.create(order=1, slug="step-2", module_id_name="mod")

        tab_flow = TabFlow(
            tab.to_arrow(),
            [
                ExecuteStep(step1, module_zipfile, {}),
                ExecuteStep(step2, module_zipfile, {}),
            ],
        )

        new_table = make_table(make_column("B", ["b"]))

        with patch.object(Kernel, "render", side_effect=mock_render(new_table)):
            with self._execute(
                workflow, tab_flow, {}, expect_log_level=logging.ERROR
            ) as (result, path):
                self.assertEqual(
                    result, StepResult(path, [Column("B", ColumnType.Text())])
                )

            self.assertEqual(
                # called with step1, then step2
                Kernel.render.call_count,
                2,
            )
            self.assertRegex(
                # Output is to the correct file
                Kernel.render.call_args[1]["output_filename"],
                r"execute-tab-output.*\.arrow",
            )
