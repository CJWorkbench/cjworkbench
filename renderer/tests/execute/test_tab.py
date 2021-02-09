import contextlib
from dataclasses import replace
import logging
import shutil
from unittest.mock import patch
from cjwkernel.chroot import EDITABLE_CHROOT
from cjwkernel.kernel import Kernel
from cjwkernel.types import RenderResult
from cjwkernel.tests.util import (
    arrow_table,
    arrow_table_context,
    assert_render_result_equals,
)
from cjwstate import s3, rabbitmq, rendercache
from cjwstate.models import Workflow
from cjwstate.tests.utils import DbTestCaseWithModuleRegistry, create_module_zipfile
from renderer.execute.tab import execute_tab_flow, ExecuteStep, TabFlow


async def fake_send(*args, **kwargs):
    pass


def mock_render(arrow_table_dict):
    def inner(
        module_zipfile,
        *,
        chroot_context,
        basedir,
        input_table,
        params,
        tab,
        fetch_result,
        output_filename,
    ):
        output_path = basedir / output_filename
        with arrow_table_context(arrow_table_dict) as arrow_table:
            shutil.copy(arrow_table.path, output_path)
            return RenderResult(table=replace(arrow_table, path=output_path))

    return inner


class TabTests(DbTestCaseWithModuleRegistry):
    @contextlib.contextmanager
    def _execute(self, workflow, flow, tab_results, expect_log_level=logging.DEBUG):
        with EDITABLE_CHROOT.acquire_context() as chroot_context:
            with chroot_context.tempdir_context(prefix="test_tab") as tempdir:
                with chroot_context.tempfile_context(
                    prefix="execute-tab-output", suffix=".arrow", dir=tempdir
                ) as out_path:
                    with self.assertLogs("renderer.execute", level=expect_log_level):
                        result = self.run_with_async_db(
                            execute_tab_flow(
                                chroot_context, workflow, flow, tab_results, out_path
                            )
                        )
                        yield result

    def test_execute_empty_tab(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        tab_flow = TabFlow(tab.to_arrow(), [])
        with self._execute(workflow, tab_flow, {}) as result:
            assert_render_result_equals(result, RenderResult())

    @patch.object(rabbitmq, "send_update_to_workflow_clients", fake_send)
    def test_execute_cache_hit(self):
        module_zipfile = create_module_zipfile("mod", spec_kwargs={"loads_data": True})
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        step1 = tab.steps.create(
            order=0, slug="step-1", last_relevant_delta_id=workflow.last_delta_id
        )
        rendercache.cache_render_result(
            workflow,
            step1,
            workflow.last_delta_id,
            RenderResult(arrow_table({"A": [1]})),
        )
        step2 = tab.steps.create(
            order=1, slug="step-2", last_relevant_delta_id=workflow.last_delta_id
        )
        rendercache.cache_render_result(
            workflow,
            step2,
            workflow.last_delta_id,
            RenderResult(arrow_table({"B": [2]})),
        )

        tab_flow = TabFlow(
            tab.to_arrow(),
            [
                ExecuteStep(step1, module_zipfile, {}),
                ExecuteStep(step2, module_zipfile, {}),
            ],
        )

        with patch.object(Kernel, "render", side_effect=mock_render({"No": ["bad"]})):
            with self._execute(workflow, tab_flow, {}) as result:
                assert_render_result_equals(
                    result, RenderResult(arrow_table({"B": [2]}), [])
                )

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

        with patch.object(Kernel, "render", side_effect=mock_render({"B": [2]})):
            with self._execute(workflow, tab_flow, {}) as result:
                expected = RenderResult(arrow_table({"B": [2]}))
                assert_render_result_equals(result, expected)

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
        rendercache.cache_render_result(
            workflow,
            step1,
            workflow.last_delta_id,
            RenderResult(arrow_table({"A": [1]})),
        )
        # step2: cached result is stale, so must be re-rendered
        step2 = tab.steps.create(
            order=1,
            slug="step-2",
            module_id_name="mod",
            last_relevant_delta_id=workflow.last_delta_id - 1,
        )
        rendercache.cache_render_result(
            workflow,
            step2,
            workflow.last_delta_id - 1,
            RenderResult(arrow_table({"B": [2]})),
        )
        step2.last_relevant_delta_id = workflow.last_delta_id
        step2.save(update_fields=["last_relevant_delta_id"])

        tab_flow = TabFlow(
            tab.to_arrow(),
            [
                ExecuteStep(step1, module_zipfile, {}),
                ExecuteStep(step2, module_zipfile, {}),
            ],
        )

        with patch.object(Kernel, "render", side_effect=mock_render({"B": [3]})):
            with self._execute(workflow, tab_flow, {}) as result:
                expected = RenderResult(arrow_table({"B": [3]}))
                assert_render_result_equals(result, expected)

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
        rendercache.cache_render_result(
            workflow,
            step1,
            workflow.last_delta_id,
            RenderResult(arrow_table({"A": [1]})),
        )
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

        with patch.object(Kernel, "render", side_effect=mock_render({"B": [2]})):
            with self._execute(
                workflow, tab_flow, {}, expect_log_level=logging.ERROR
            ) as result:
                expected = RenderResult(arrow_table({"B": [2]}))
                assert_render_result_equals(result, expected)

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
