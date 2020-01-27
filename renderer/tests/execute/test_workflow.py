import asyncio
from collections import namedtuple
from dataclasses import replace
import logging
import shutil
import textwrap
import unittest
from unittest.mock import Mock, patch
from cjwkernel.errors import ModuleExitedError
from cjwkernel.kernel import Kernel
from cjwkernel.types import I18nMessage, Params, RenderError, RenderResult
from cjwkernel.tests.util import (
    arrow_table,
    arrow_table_context,
    assert_render_result_equals,
)
from cjwstate import clientside, rabbitmq
from cjwstate.models import Workflow
from cjwstate.models.commands import InitWorkflowCommand
from cjwstate.rendercache import cache_render_result, open_cached_render_result
from cjwstate.tests.utils import DbTestCaseWithModuleRegistry, create_module_zipfile
from renderer.execute.types import UnneededExecution
from renderer.execute.workflow import execute_workflow, partition_ready_and_dependent


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
        output_filename
    ):
        output_path = basedir / output_filename
        with arrow_table_context(arrow_table_dict) as arrow_table:
            shutil.copy(arrow_table.path, output_path)
            return RenderResult(table=replace(arrow_table, path=output_path))

    return inner


def cached_render_result_revision_list(workflow):
    return list(
        workflow.tabs.first().live_wf_modules.values_list(
            "cached_render_result_delta_id", flat=True
        )
    )


class WorkflowTests(DbTestCaseWithModuleRegistry):
    def _execute(self, workflow):
        with self.assertLogs(level=logging.DEBUG):
            self.run_with_async_db(execute_workflow(workflow, workflow.last_delta_id))

    @patch.object(rabbitmq, "send_update_to_workflow_clients", fake_send)
    def test_execute_new_revision(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        delta1 = workflow.last_delta
        create_module_zipfile(
            "mod",
            python_code='import pandas as pd\ndef render(table, params): return pd.DataFrame({"B": [2]})',
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

        self._execute(workflow)

        wf_module.refresh_from_db()

        with open_cached_render_result(wf_module.cached_render_result) as result:
            assert_render_result_equals(result, RenderResult(arrow_table({"B": [2]})))

    @patch.object(rabbitmq, "send_update_to_workflow_clients", fake_send)
    def test_execute_tempdir_not_in_tmpfs(self):
        # /tmp is RAM; /var/tmp is disk. Assert big files go on disk.
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        delta1 = workflow.last_delta
        create_module_zipfile("mod")
        tab.wf_modules.create(
            order=0,
            slug="step-1",
            last_relevant_delta_id=delta1.id - 1,
            module_id_name="mod",
        )

        with patch.object(Kernel, "render", side_effect=mock_render({"B": [2]})):
            self._execute(workflow)
            self.assertRegex(str(Kernel.render.call_args[1]["basedir"]), r"/var/tmp/")

    def test_execute_race_delete_workflow(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        create_module_zipfile("mod")
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

        def render_and_delete(*args, **kwargs):
            # Render successfully. Then delete `workflow`, which should force
            # us to cancel before the next render().
            ret = mock_render({"B": [2]})(*args, **kwargs)
            Workflow.objects.filter(id=workflow.id).delete()
            return ret

        with patch.object(Kernel, "render", side_effect=render_and_delete):
            with self.assertRaises(UnneededExecution):
                self._execute(workflow)

            Kernel.render.assert_called_once()  # never called with step-2.

    @patch.object(rabbitmq, "send_update_to_workflow_clients")
    def test_execute_mark_unreachable(self, send_update):
        future_none = asyncio.Future()
        future_none.set_result(None)
        send_update.return_value = future_none

        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        delta_id = workflow.last_delta_id
        create_module_zipfile(
            "mod", python_code='def render(table, params): return "error, not warning"'
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

        error_result = RenderResult(
            errors=[RenderError(I18nMessage.TODO_i18n("error, not warning"))]
        )

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

        send_update.assert_called_with(
            workflow.id,
            clientside.Update(
                steps={
                    wf_module3.id: clientside.StepUpdate(
                        render_result=wf_module3.cached_render_result
                    )
                }
            ),
        )

    @patch.object(rabbitmq, "send_update_to_workflow_clients", fake_send)
    def test_execute_migrate_params_invalid_params_are_coerced(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        delta1 = workflow.last_delta
        create_module_zipfile(
            "mod",
            spec_kwargs={"parameters": [{"id_name": "x", "type": "string"}]},
            python_code=textwrap.dedent(
                """
                import json
                def render(table, params): return "params: " + json.dumps(params)
                def migrate_params(params): return {"x": 2}  # wrong type
                """
            ),
        )
        wf_module = tab.wf_modules.create(
            order=0,
            slug="step-1",
            last_relevant_delta_id=delta1.id,
            module_id_name="mod",
        )

        self._execute(workflow)

        wf_module.refresh_from_db()
        self.assertEqual(
            wf_module.cached_render_result_errors,
            [RenderError(I18nMessage.TODO_i18n('params: {"x": "2"}'))],
        )

    @patch.object(rabbitmq, "send_update_to_workflow_clients", fake_send)
    def test_execute_migrate_params_module_error_gives_default_params(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        delta1 = workflow.last_delta
        create_module_zipfile(
            "mod",
            spec_kwargs={
                "parameters": [{"id_name": "x", "type": "string", "default": "def"}]
            },
            python_code=textwrap.dedent(
                """
                import json
                def render(table, params): return "params: " + json.dumps(params)
                def migrate_params(params): cause_module_error()  # NameError
                """
            ),
        )
        wf_module = tab.wf_modules.create(
            order=0,
            slug="step-1",
            last_relevant_delta_id=delta1.id,
            module_id_name="mod",
            params={"x": "good"},
        )

        self._execute(workflow)

        wf_module.refresh_from_db()
        self.assertEqual(
            wf_module.cached_render_result_errors,
            [RenderError(I18nMessage.TODO_i18n('params: {"x": "def"}'))],
        )

    @patch.object(rabbitmq, "send_update_to_workflow_clients", fake_send)
    def test_execute_cache_hit(self):
        workflow = Workflow.objects.create()
        create_module_zipfile("mod")
        tab = workflow.tabs.create(position=0)
        delta = InitWorkflowCommand.create(workflow)
        wf_module1 = tab.wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="mod",
            last_relevant_delta_id=delta.id,
        )
        cache_render_result(
            workflow, wf_module1, delta.id, RenderResult(arrow_table({"A": [1]}))
        )
        wf_module2 = tab.wf_modules.create(
            order=1,
            slug="step-2",
            module_id_name="mod",
            last_relevant_delta_id=delta.id,
        )
        cache_render_result(
            workflow, wf_module2, delta.id, RenderResult(arrow_table({"B": [2]}))
        )

        with patch.object(Kernel, "render", return_value=None):
            self._execute(workflow)
            Kernel.render.assert_not_called()

    @patch.object(rabbitmq, "send_update_to_workflow_clients", fake_send)
    def test_resume_without_rerunning_unneeded_renders(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        delta_id = workflow.last_delta_id
        create_module_zipfile(
            # If this runs on wf_module1, it'll return pd.DataFrame().
            # If this runs on wf_module2, it'll return wf_module1-output * 2.
            # ... wf_module2's output depends on whether we run this on
            # wf_module1.
            "mod",
            python_code="def render(table, params): return table * 2",
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

        self._execute(workflow)

        wf_module2.refresh_from_db()
        with open_cached_render_result(wf_module2.cached_render_result) as actual:
            assert_render_result_equals(actual, RenderResult(arrow_table({"A": [2]})))

    @patch.object(rabbitmq, "send_update_to_workflow_clients", fake_send)
    @patch("renderer.notifications.email_output_delta")
    def test_email_delta(self, email):
        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        delta1 = InitWorkflowCommand.create(workflow)
        create_module_zipfile(
            "mod",
            python_code='import pandas as pd\ndef render(table, params): return pd.DataFrame({"A": [2]})',
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

        self._execute(workflow)

        email.assert_called()

    @patch.object(rabbitmq, "send_update_to_workflow_clients", fake_send)
    @patch("renderer.notifications.email_output_delta")
    def test_email_no_delta_when_not_changed(self, email):
        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        delta1 = InitWorkflowCommand.create(workflow)
        create_module_zipfile(
            "mod",
            python_code='import pandas as pd\ndef render(table, params): return pd.DataFrame({"A": [1]})',
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

        self._execute(workflow)

        email.assert_not_called()

    @patch.object(rabbitmq, "send_update_to_workflow_clients", fake_send)
    @patch("renderer.notifications.email_output_delta")
    def test_email_no_delta_when_no_cached_render_result(self, email):
        # No cached render result means one of two things:
        #
        # 1. This is a new module (in which case, why email the user?)
        # 2. We cleared the render cache (in which case, better to skip emailing a few
        #    users than to email _every_ user that results have changed when they haven't)

        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        delta1 = InitWorkflowCommand.create(workflow)
        create_module_zipfile(
            "mod",
            python_code='import pandas as pd\ndef render(table, params): return pd.DataFrame({"A": [1]})',
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
