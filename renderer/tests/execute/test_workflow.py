import asyncio
from collections import namedtuple
import logging
import unittest
from unittest.mock import Mock, patch
import pandas as pd
from cjwkernel.errors import ModuleExitedError
from cjwkernel.types import I18nMessage, Params, RenderError, RenderResult
from cjwkernel.tests.util import arrow_table, assert_render_result_equals
from cjwstate.rendercache import cache_render_result, open_cached_render_result
from cjwstate.models import ModuleVersion, Workflow
from cjwstate.models.commands import InitWorkflowCommand
from cjwstate.modules.loaded_module import LoadedModule
from cjwstate.tests.utils import DbTestCase
from renderer.execute.types import UnneededExecution
from renderer.execute.workflow import execute_workflow, partition_ready_and_dependent


table_csv = "A,B\n1,2\n3,4"
table_dataframe = pd.DataFrame({"A": [1, 3], "B": [2, 4]})


future_none = asyncio.Future()
future_none.set_result(None)


async def fake_send(*args, **kwargs):
    pass


def cached_render_result_revision_list(workflow):
    return list(
        workflow.tabs.first().live_wf_modules.values_list(
            "cached_render_result_delta_id", flat=True
        )
    )


class WorkflowTests(DbTestCase):
    def _execute(self, workflow):
        with self.assertLogs(level=logging.DEBUG):
            self.run_with_async_db(execute_workflow(workflow, workflow.last_delta_id))

    @patch.object(LoadedModule, "for_module_version")
    @patch("server.websockets.ws_client_send_delta_async", fake_send)
    def test_execute_new_revision(self, fake_load_module):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        delta1 = workflow.last_delta
        ModuleVersion.create_or_replace_from_spec(
            {"id_name": "mod", "name": "Mod", "category": "Clean", "parameters": []}
        )
        wf_module = tab.wf_modules.create(
            order=0,
            slug="step-1",
            last_relevant_delta_id=delta1.id,
            module_id_name="mod",
        )

        result1 = RenderResult(arrow_table({"A": [1]}))
        cache_render_result(workflow, wf_module, delta1.id, result1)

        delta2 = InitWorkflowCommand.create(workflow)
        wf_module.last_relevant_delta_id = delta2.id
        wf_module.save(update_fields=["last_relevant_delta_id"])

        result2 = RenderResult(arrow_table({"B": [2]}))
        fake_module = Mock(LoadedModule)
        fake_module.migrate_params.return_value = {}
        fake_load_module.return_value = fake_module
        fake_module.render.return_value = result2

        self._execute(workflow)

        wf_module.refresh_from_db()

        with open_cached_render_result(wf_module.cached_render_result) as result:
            assert_render_result_equals(result, result2)

    @patch.object(LoadedModule, "for_module_version")
    @patch("server.websockets.ws_client_send_delta_async", fake_send)
    def test_execute_tempdir_not_in_tmpfs(self, fake_load_module):
        # /tmp is RAM; /var/tmp is disk. Assert big files go on disk.
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        delta1 = workflow.last_delta
        ModuleVersion.create_or_replace_from_spec(
            {"id_name": "mod", "name": "Mod", "category": "Clean", "parameters": []}
        )
        tab.wf_modules.create(
            order=0,
            slug="step-1",
            last_relevant_delta_id=delta1.id - 1,
            module_id_name="mod",
        )

        result2 = RenderResult(arrow_table({"B": [2]}))
        fake_load_module.return_value.migrate_params.return_value = {}
        fake_load_module.return_value.render.return_value = result2

        self._execute(workflow)

        self.assertRegex(
            str(fake_load_module.return_value.render.call_args[1]["basedir"]),
            r"/var/tmp/",
        )

    @patch.object(LoadedModule, "for_module_version")
    def test_execute_race_delete_workflow(self, fake_load_module):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        ModuleVersion.create_or_replace_from_spec(
            {"id_name": "mod", "name": "Mod", "category": "Clean", "parameters": []}
        )
        tab.wf_modules.create(
            order=0,
            slug="step-1",
            last_relevant_delta_id=workflow.last_delta_id,
            module_id_name="mod",
        )
        tab.wf_modules.create(
            order=1,
            slug="step-2",
            last_relevant_delta_id=workflow.last_delta_id,
            module_id_name="mod",
        )

        def load_module_and_delete(module_version):
            Workflow.objects.filter(id=workflow.id).delete()
            fake_module = Mock(LoadedModule)
            fake_module.migrate_params.return_value = {}
            fake_module.render.return_value = RenderResult(arrow_table({"A": [1]}))
            return fake_module

        fake_load_module.side_effect = load_module_and_delete

        with self.assertRaises(UnneededExecution):
            self._execute(workflow)

    @patch.object(LoadedModule, "for_module_version")
    @patch("server.websockets.ws_client_send_delta_async")
    def test_execute_mark_unreachable(self, send_delta_async, fake_load_module):
        send_delta_async.return_value = future_none

        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        delta_id = workflow.last_delta_id
        ModuleVersion.create_or_replace_from_spec(
            {"id_name": "mod", "name": "Mod", "category": "Clean", "parameters": []}
        )
        wf_module1 = tab.wf_modules.create(
            order=0,
            slug="step-1",
            last_relevant_delta_id=delta_id,
            module_id_name="mod",
        )
        wf_module2 = tab.wf_modules.create(
            order=1,
            slug="step-2",
            last_relevant_delta_id=delta_id,
            module_id_name="mod",
        )
        wf_module3 = tab.wf_modules.create(
            order=2,
            slug="step-3",
            last_relevant_delta_id=delta_id,
            module_id_name="mod",
        )

        fake_module = Mock(LoadedModule)
        fake_load_module.return_value = fake_module
        fake_module.migrate_params.return_value = {}
        error_result = RenderResult(
            errors=[RenderError(I18nMessage.TODO_i18n("error, not warning"))]
        )
        fake_module.render.return_value = error_result

        self._execute(workflow)

        wf_module1.refresh_from_db()
        self.assertEqual(wf_module1.cached_render_result.status, "error")
        with open_cached_render_result(wf_module1.cached_render_result) as result:
            assert_render_result_equals(result, error_result)

        wf_module2.refresh_from_db()
        self.assertEqual(wf_module2.cached_render_result.status, "unreachable")
        with open_cached_render_result(wf_module2.cached_render_result) as result:
            assert_render_result_equals(result, RenderResult())

        wf_module3.refresh_from_db()
        self.assertEqual(wf_module3.cached_render_result.status, "unreachable")
        with open_cached_render_result(wf_module3.cached_render_result) as result:
            assert_render_result_equals(result, RenderResult())

        send_delta_async.assert_called_with(
            workflow.id,
            {
                "updateWfModules": {
                    str(wf_module3.id): {
                        "output_status": "unreachable",
                        "quick_fixes": [],
                        "output_error": "",
                        "output_columns": [],
                        "output_n_rows": 0,
                        "cached_render_result_delta_id": delta_id,
                    }
                }
            },
        )

    @patch.object(LoadedModule, "for_module_version")
    @patch("server.websockets.ws_client_send_delta_async", fake_send)
    def test_execute_migrate_params_invalid_params_are_coerced(self, fake_load_module):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        delta1 = workflow.last_delta
        ModuleVersion.create_or_replace_from_spec(
            {
                "id_name": "mod",
                "name": "Mod",
                "category": "Clean",
                "parameters": [{"type": "string", "id_name": "x"}],
            }
        )
        tab.wf_modules.create(
            order=0,
            slug="step-1",
            last_relevant_delta_id=delta1.id,
            module_id_name="mod",
        )

        def render(*args, params, **kwargs):
            self.assertEqual(params, Params({"x": "2"}))
            return RenderResult(arrow_table({"A": [1]}))

        # make migrate_params() return an int instead of a str. Assume
        # ParamDType.coerce() will cast it to str.
        fake_load_module.return_value.migrate_params.return_value = {"x": 2}
        fake_load_module.return_value.render.side_effect = render
        self._execute(workflow)
        fake_load_module.return_value.render.assert_called()

    @patch.object(LoadedModule, "for_module_version")
    @patch("server.websockets.ws_client_send_delta_async", fake_send)
    def test_execute_migrate_params_module_error_gives_default_params(
        self, fake_load_module
    ):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        delta1 = workflow.last_delta
        ModuleVersion.create_or_replace_from_spec(
            {
                "id_name": "mod",
                "name": "Mod",
                "category": "Clean",
                "parameters": [{"type": "string", "id_name": "x", "default": "def"}],
            }
        )
        tab.wf_modules.create(
            order=0,
            slug="step-1",
            last_relevant_delta_id=delta1.id,
            module_id_name="mod",
        )

        def render(*args, params, **kwargs):
            self.assertEqual(params, Params({"x": "def"}))  # default params
            return RenderResult(arrow_table({"A": [1]}))

        # make migrate_params() raise an error.
        fake_load_module.return_value.migrate_params.side_effect = ModuleExitedError(
            -9, ""
        )
        fake_load_module.return_value.render.side_effect = render
        self._execute(workflow)
        fake_load_module.return_value.render.assert_called()

    @patch.object(LoadedModule, "for_module_version")
    @patch("server.websockets.ws_client_send_delta_async", fake_send)
    def test_execute_cache_hit(self, fake_module):
        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        delta = InitWorkflowCommand.create(workflow)
        wf_module1 = tab.wf_modules.create(
            order=0, slug="step-1", last_relevant_delta_id=delta.id
        )
        cache_render_result(
            workflow, wf_module1, delta.id, RenderResult(arrow_table({"A": [1]}))
        )
        wf_module2 = tab.wf_modules.create(
            order=1, slug="step-2", last_relevant_delta_id=delta.id
        )
        cache_render_result(
            workflow, wf_module2, delta.id, RenderResult(arrow_table({"B": [2]}))
        )

        self._execute(workflow)

        fake_module.assert_not_called()

    @patch.object(LoadedModule, "for_module_version")
    @patch("server.websockets.ws_client_send_delta_async", fake_send)
    def test_resume_without_rerunning_unneeded_renders(self, fake_load_module):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        delta_id = workflow.last_delta_id
        ModuleVersion.create_or_replace_from_spec(
            {"id_name": "mod", "name": "Mod", "category": "Clean", "parameters": []}
        )

        # wf_module1: has a valid, cached result
        wf_module1 = tab.wf_modules.create(
            order=0,
            slug="step-1",
            last_relevant_delta_id=delta_id,
            module_id_name="mod",
        )
        cache_render_result(
            workflow, wf_module1, delta_id, RenderResult(arrow_table({"A": [1]}))
        )

        # wf_module2: has no cached result (must be rendered)
        wf_module2 = tab.wf_modules.create(
            order=1,
            slug="step-2",
            last_relevant_delta_id=delta_id,
            module_id_name="mod",
        )

        fake_loaded_module = Mock(LoadedModule)
        fake_loaded_module.migrate_params.return_value = {}
        fake_load_module.return_value = fake_loaded_module
        result2 = RenderResult(arrow_table({"A": [2]}))

        fake_loaded_module.render.return_value = result2
        self._execute(workflow)
        fake_loaded_module.render.assert_called_once()  # only with module2

        wf_module2.refresh_from_db()
        with open_cached_render_result(wf_module2.cached_render_result) as actual:
            assert_render_result_equals(actual, result2)

    @patch.object(LoadedModule, "for_module_version")
    @patch("server.websockets.ws_client_send_delta_async", fake_send)
    @patch("renderer.notifications.email_output_delta")
    def test_email_delta(self, email, fake_load_module):
        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        delta1 = InitWorkflowCommand.create(workflow)
        ModuleVersion.create_or_replace_from_spec(
            {"id_name": "mod", "name": "Mod", "category": "Clean", "parameters": []}
        )
        wf_module = tab.wf_modules.create(
            order=0,
            slug="step-1",
            last_relevant_delta_id=delta1.id,
            module_id_name="mod",
            notifications=True,
        )
        cache_render_result(
            workflow, wf_module, delta1.id, RenderResult(arrow_table({"A": [1]}))
        )

        # Make a new delta, so we need to re-render.
        delta2 = InitWorkflowCommand.create(workflow)
        wf_module.last_relevant_delta_id = delta2.id
        wf_module.save(update_fields=["last_relevant_delta_id"])

        fake_loaded_module = Mock(LoadedModule)
        fake_load_module.return_value = fake_loaded_module
        fake_loaded_module.migrate_params.return_value = {}
        fake_loaded_module.render.return_value = RenderResult(arrow_table({"A": [2]}))

        self._execute(workflow)

        email.assert_called()

    @patch.object(LoadedModule, "for_module_version")
    @patch("server.websockets.ws_client_send_delta_async", fake_send)
    @patch("renderer.notifications.email_output_delta")
    def test_email_no_delta_when_not_changed(self, email, fake_load_module):
        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        delta1 = InitWorkflowCommand.create(workflow)
        ModuleVersion.create_or_replace_from_spec(
            {"id_name": "mod", "name": "Mod", "category": "Clean", "parameters": []}
        )
        wf_module = tab.wf_modules.create(
            order=0,
            slug="step-1",
            last_relevant_delta_id=delta1.id,
            module_id_name="mod",
            notifications=True,
        )
        cache_render_result(
            workflow, wf_module, delta1.id, RenderResult(arrow_table({"A": [1]}))
        )

        # Make a new delta, so we need to re-render. Give it the same output.
        delta2 = InitWorkflowCommand.create(workflow)
        wf_module.last_relevant_delta_id = delta2.id
        wf_module.save(update_fields=["last_relevant_delta_id"])

        fake_loaded_module = Mock(LoadedModule)
        fake_load_module.return_value = fake_loaded_module
        fake_loaded_module.migrate_params.return_value = {}
        fake_loaded_module.render.return_value = RenderResult(arrow_table({"A": [1]}))

        self._execute(workflow)

        email.assert_not_called()

    @patch.object(LoadedModule, "for_module_version")
    @patch("server.websockets.ws_client_send_delta_async", fake_send)
    @patch("renderer.notifications.email_output_delta")
    def test_email_no_delta_when_no_cached_render_result(self, email, fake_load_module):
        # No cached render result means one of two things:
        #
        # 1. This is a new module (in which case, why email the user?)
        # 2. We cleared the render cache (in which case, better to skip emailing a few
        #    users than to email _every_ user that results have changed when they haven't)

        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        delta1 = InitWorkflowCommand.create(workflow)
        ModuleVersion.create_or_replace_from_spec(
            {"id_name": "mod", "name": "Mod", "category": "Clean", "parameters": []}
        )
        wf_module = tab.wf_modules.create(
            order=0,
            slug="step-1",
            last_relevant_delta_id=delta1.id,
            module_id_name="mod",
            notifications=True,
        )

        # Make a new delta, so we need to re-render. Give it the same output.
        delta2 = InitWorkflowCommand.create(workflow)
        wf_module.last_relevant_delta_id = delta2.id
        wf_module.save(update_fields=["last_relevant_delta_id"])

        fake_loaded_module = Mock(LoadedModule)
        fake_load_module.return_value = fake_loaded_module
        fake_loaded_module.migrate_params.return_value = {}
        fake_loaded_module.render.return_value = RenderResult(arrow_table({"A": [1]}))

        self._execute(workflow)

        email.assert_not_called()


class PartitionReadyAndDependentTests(unittest.TestCase):
    MockTabFlow = namedtuple("MockTabFlow", ("tab_slug", "input_tab_slugs"))

    def test_empty_list(self):
        self.assertEqual(([], []), partition_ready_and_dependent([]))

    def test_no_tab_params(self):
        flows = [
            self.MockTabFlow("t1", frozenset()),
            self.MockTabFlow("t2", frozenset()),
            self.MockTabFlow("t3", frozenset()),
        ]
        self.assertEqual((flows, []), partition_ready_and_dependent(flows))

    def test_tab_chain(self):
        flows = [
            self.MockTabFlow("t1", frozenset({"t2"})),
            self.MockTabFlow("t2", frozenset({"t3"})),
            self.MockTabFlow("t3", frozenset()),
        ]
        self.assertEqual((flows[2:], flows[:2]), partition_ready_and_dependent(flows))

    def test_missing_tabs(self):
        flows = [
            self.MockTabFlow("t1", frozenset({"t4"})),
            self.MockTabFlow("t2", frozenset({"t4"})),
            self.MockTabFlow("t3", frozenset()),
        ]
        self.assertEqual((flows, []), partition_ready_and_dependent(flows))

    def test_cycle(self):
        flows = [
            self.MockTabFlow("t1", frozenset({"t2"})),
            self.MockTabFlow("t2", frozenset({"t1"})),
            self.MockTabFlow("t3", frozenset()),
        ]
        self.assertEqual((flows[2:], flows[:2]), partition_ready_and_dependent(flows))

    def test_tab_self_reference(self):
        flows = [self.MockTabFlow("t1", frozenset({"t1"}))]
        self.assertEqual(([], flows), partition_ready_and_dependent(flows))
