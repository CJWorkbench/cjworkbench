import asyncio
import contextlib
import logging
from unittest.mock import patch
import pandas as pd
from cjwkernel.types import RenderResult
from cjwkernel.tests.util import arrow_table, assert_render_result_equals
from cjwkernel.chroot import EDITABLE_CHROOT
from cjwstate import minio, rendercache
from cjwstate.models import ModuleVersion, Workflow
from cjwstate.models.param_spec import ParamDType
from cjwstate.modules.loaded_module import LoadedModule
from cjwstate.tests.utils import DbTestCase
from renderer.execute.tab import execute_tab_flow, ExecuteStep, TabFlow


table_csv = "A,B\n1,2\n3,4"
table_dataframe = pd.DataFrame({"A": [1, 3], "B": [2, 4]})


future_none = asyncio.Future()
future_none.set_result(None)


async def fake_send(*args, **kwargs):
    pass


class TabTests(DbTestCase):
    @contextlib.contextmanager
    def _execute(self, workflow, flow, tab_results, expect_log_level=logging.DEBUG):
        with EDITABLE_CHROOT.acquire_context() as chroot_context:
            with chroot_context.tempdir_context(prefix="test_tab") as tempdir:
                with chroot_context.tempfile_context(
                    prefix="execute-tab-output", suffix=".arrow", dir=tempdir
                ) as out_path:
                    with self.assertLogs(level=expect_log_level):
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

    @patch.object(LoadedModule, "for_module_version")
    @patch("server.websockets.ws_client_send_delta_async", fake_send)
    def test_execute_cache_hit(self, fake_module):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        step1 = tab.wf_modules.create(
            order=0, slug="step-1", last_relevant_delta_id=workflow.last_delta_id
        )
        rendercache.cache_render_result(
            workflow,
            step1,
            workflow.last_delta_id,
            RenderResult(arrow_table({"A": [1]})),
        )
        step2 = tab.wf_modules.create(
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
                ExecuteStep(step1, ParamDType.Dict({}), {}),
                ExecuteStep(step2, ParamDType.Dict({}), {}),
            ],
        )

        with self._execute(workflow, tab_flow, {}) as result:
            assert_render_result_equals(
                result, RenderResult(arrow_table({"B": [2]}), [])
            )

        fake_module.assert_not_called()

    @patch.object(LoadedModule, "for_module_version")
    @patch("server.websockets.ws_client_send_delta_async", fake_send)
    def test_execute_cache_miss(self, fake_load_module):
        ModuleVersion.create_or_replace_from_spec(
            {"id_name": "mod", "name": "Mod", "category": "Clean", "parameters": []}
        )
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        step1 = tab.wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="mod",
            last_relevant_delta_id=workflow.last_delta_id,
        )
        step2 = tab.wf_modules.create(
            order=1,
            slug="step-2",
            module_id_name="mod",
            last_relevant_delta_id=workflow.last_delta_id,
        )

        tab_flow = TabFlow(
            tab.to_arrow(),
            [
                ExecuteStep(step1, ParamDType.Dict({}), {}),
                ExecuteStep(step2, ParamDType.Dict({}), {}),
            ],
        )

        expected = RenderResult(arrow_table({"B": [2]}))
        fake_load_module.return_value.render.return_value = expected
        with self._execute(workflow, tab_flow, {}) as result:
            assert_render_result_equals(result, expected)

        self.assertEqual(
            fake_load_module.return_value.render.call_count, 2  # step2, not step1
        )
        self.assertRegex(
            # Output is to the correct file
            fake_load_module.return_value.render.call_args[1]["output_filename"],
            r"execute-tab-output.*\.arrow",
        )

    @patch.object(LoadedModule, "for_module_version")
    @patch("server.websockets.ws_client_send_delta_async", fake_send)
    def test_execute_partial_cache_hit(self, fake_load_module):
        ModuleVersion.create_or_replace_from_spec(
            {"id_name": "mod", "name": "Mod", "category": "Clean", "parameters": []}
        )
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        # step1: cached result is fresh. Should not render.
        step1 = tab.wf_modules.create(
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
        step2 = tab.wf_modules.create(
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
                ExecuteStep(step1, ParamDType.Dict({}), {}),
                ExecuteStep(step2, ParamDType.Dict({}), {}),
            ],
        )

        expected = RenderResult(arrow_table({"B": [3]}))
        fake_load_module.return_value.render.return_value = expected
        with self._execute(workflow, tab_flow, {}) as result:
            assert_render_result_equals(result, expected)

        fake_load_module.return_value.render.assert_called_once()  # step2, not step1
        self.assertRegex(
            # Output is to the correct file
            fake_load_module.return_value.render.call_args[1]["output_filename"],
            r"execute-tab-output.*\.arrow",
        )

    @patch.object(LoadedModule, "for_module_version")
    @patch("server.websockets.ws_client_send_delta_async", fake_send)
    def test_resume_backtrack_on_corrupt_cache_error(self, fake_load_module):
        ModuleVersion.create_or_replace_from_spec(
            {"id_name": "mod", "name": "Mod", "category": "Clean", "parameters": []}
        )
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        # step1: cached result is fresh -- but CORRUPT
        step1 = tab.wf_modules.create(
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
        minio.put_bytes(
            # Write corrupted data -- will lead to CorruptCacheError
            rendercache.io.BUCKET,
            rendercache.io.crr_parquet_key(step1.cached_render_result),
            b"CORRUPT",
        )
        # step2: no cached result -- must re-render
        step2 = tab.wf_modules.create(order=1, slug="step-2", module_id_name="mod")

        tab_flow = TabFlow(
            tab.to_arrow(),
            [
                ExecuteStep(step1, ParamDType.Dict({}), {}),
                ExecuteStep(step2, ParamDType.Dict({}), {}),
            ],
        )

        expected = RenderResult(arrow_table({"B": [2]}))
        fake_load_module.return_value.render.return_value = expected
        with self._execute(
            workflow, tab_flow, {}, expect_log_level=logging.ERROR
        ) as result:
            assert_render_result_equals(result, expected)

        self.assertEqual(
            # called with step1, then step2
            fake_load_module.return_value.render.call_count,
            2,
        )
        self.assertRegex(
            # Output is to the correct file
            fake_load_module.return_value.render.call_args[1]["output_filename"],
            r"execute-tab-output.*\.arrow",
        )
