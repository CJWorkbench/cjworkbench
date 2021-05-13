import asyncio
import logging
import shutil
import textwrap
import unittest
from collections import namedtuple
from unittest.mock import patch

import pyarrow as pa
from cjwmodule.arrow.testing import assert_arrow_table_equals, make_column, make_table

from cjwkernel.kernel import Kernel
from cjwkernel.i18n import TODO_i18n
from cjwkernel.types import RenderError, RenderResult
from cjwkernel.tests.util import arrow_table_context
from cjwstate import clientside, rabbitmq
from cjwstate.models import Workflow
from cjwstate.rendercache import open_cached_render_result
from cjwstate.rendercache.testing import write_to_rendercache
from cjwstate.tests.utils import (
    DbTestCaseWithModuleRegistry,
    create_module_zipfile,
    create_test_user,
)
from renderer.execute.types import UnneededExecution
from renderer.execute.workflow import execute_workflow, partition_ready_and_dependent


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
        tab_name,
        fetch_result,
        tab_outputs,
        uploaded_files,
        output_filename,
    ):
        output_path = basedir / output_filename
        with arrow_table_context(arrow_table) as (table_path, table):
            shutil.copy(table_path, output_path)
            return RenderResult(errors=[])

    return inner


class WorkflowTests(DbTestCaseWithModuleRegistry):
    def _execute(self, workflow):
        with self.assertLogs(level=logging.DEBUG):
            self.run_with_async_db(execute_workflow(workflow, workflow.last_delta_id))

    @patch.object(rabbitmq, "send_update_to_workflow_clients", fake_send)
    def test_execute_new_revision(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        create_module_zipfile(
            "mod",
            spec_kwargs={"loads_data": True},
            python_code='import pandas as pd\ndef render(table, params): return pd.DataFrame({"B": [2]})',
        )
        step = tab.steps.create(
            order=0,
            slug="step-1",
            last_relevant_delta_id=2,
            module_id_name="mod",
        )
        # stale
        write_to_rendercache(workflow, step, 1, make_table(make_column("A", ["a"])))

        self._execute(workflow)

        step.refresh_from_db()

        with open_cached_render_result(step.cached_render_result) as result:
            assert_arrow_table_equals(result.table, make_table(make_column("B", [2])))

    @patch.object(rabbitmq, "send_update_to_workflow_clients", fake_send)
    def test_execute_tempdir_not_in_tmpfs(self):
        # /tmp is RAM; /var/tmp is disk. Assert big files go on disk.
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        create_module_zipfile("mod", spec_kwargs={"loads_data": True})
        tab.steps.create(order=0, slug="step-1", module_id_name="mod")

        with patch.object(
            Kernel, "render", side_effect=mock_render(make_table(make_column("B", [2])))
        ):
            self._execute(workflow)
            self.assertRegex(str(Kernel.render.call_args[1]["basedir"]), r"/var/tmp/")

    def test_execute_race_delete_workflow(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        create_module_zipfile("mod", spec_kwargs={"loads_data": True})
        tab.steps.create(order=0, slug="step-1", module_id_name="mod")
        tab.steps.create(order=1, slug="step-2", module_id_name="mod")

        def render_and_delete(*args, **kwargs):
            # Render successfully. Then delete `workflow`, which should force
            # us to cancel before the next render().
            ret = mock_render(make_table(make_column("B", [2])))(*args, **kwargs)
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
        create_module_zipfile(
            "mod",
            spec_kwargs={"loads_data": True},
            python_code='def render(table, params): return "error, not warning"',
        )
        step1 = tab.steps.create(order=0, slug="step-1", module_id_name="mod")
        step2 = tab.steps.create(order=1, slug="step-2", module_id_name="mod")
        step3 = tab.steps.create(order=2, slug="step-3", module_id_name="mod")

        self._execute(workflow)

        # step1: error
        step1.refresh_from_db()
        with open_cached_render_result(step1.cached_render_result) as result:
            self.assertEqual(result.path.read_bytes(), b"")
            self.assertEqual(
                step1.cached_render_result.errors,
                [RenderError(TODO_i18n("error, not warning"))],
            )

        # step2, step3: unreachable (no errors, no table data)
        step2.refresh_from_db()
        self.assertEqual(step2.cached_render_result.status, "unreachable")
        with open_cached_render_result(step2.cached_render_result) as result:
            self.assertEqual(result.path.read_bytes(), b"")
            self.assertEqual(step2.cached_render_result.errors, [])

        step3.refresh_from_db()
        with open_cached_render_result(step3.cached_render_result) as result:
            self.assertEqual(result.path.read_bytes(), b"")
            self.assertEqual(step3.cached_render_result.errors, [])

        send_update.assert_called_with(
            workflow.id,
            clientside.Update(
                steps={
                    step3.id: clientside.StepUpdate(
                        render_result=step3.cached_render_result, module_slug="mod"
                    )
                }
            ),
        )

    @patch.object(rabbitmq, "send_update_to_workflow_clients", fake_send)
    def test_execute_migrate_params_invalid_params_become_default(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        create_module_zipfile(
            "mod",
            spec_kwargs={
                "loads_data": True,
                "parameters": [{"id_name": "x", "type": "string", "default": "blah"}],
            },
            python_code=textwrap.dedent(
                """
                import json
                def render(table, params): return "params: " + json.dumps(params)
                def migrate_params(params): return {"x": 2}  # wrong type
                """
            ),
        )
        step = tab.steps.create(order=0, slug="step-1", module_id_name="mod")

        self._execute(workflow)

        step.refresh_from_db()
        self.assertEqual(
            step.cached_render_result_errors,
            [RenderError(TODO_i18n('params: {"x": "blah"}'))],
        )

    @patch.object(rabbitmq, "send_update_to_workflow_clients", fake_send)
    def test_execute_migrate_params_module_error_gives_default_params(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        create_module_zipfile(
            "mod",
            spec_kwargs={
                "loads_data": True,
                "parameters": [{"id_name": "x", "type": "string", "default": "def"}],
            },
            python_code=textwrap.dedent(
                """
                import json
                def render(table, params): return "params: " + json.dumps(params)
                def migrate_params(params): cause_module_error()  # NameError
                """
            ),
        )
        step = tab.steps.create(
            order=0, slug="step-1", module_id_name="mod", params={"x": "good"}
        )

        self._execute(workflow)

        step.refresh_from_db()
        self.assertEqual(
            step.cached_render_result_errors,
            [RenderError(TODO_i18n('params: {"x": "def"}'))],
        )

    @patch.object(rabbitmq, "send_update_to_workflow_clients", fake_send)
    def test_execute_cache_hit(self):
        workflow = Workflow.objects.create()
        create_module_zipfile("mod")
        tab = workflow.tabs.create(position=0)
        step1 = tab.steps.create(
            order=0,
            slug="step-1",
            module_id_name="mod",
            last_relevant_delta_id=2,
        )
        write_to_rendercache(workflow, step1, 2, make_table(make_column("A", ["a"])))
        step2 = tab.steps.create(
            order=1,
            slug="step-2",
            module_id_name="mod",
            last_relevant_delta_id=1,
        )
        write_to_rendercache(workflow, step2, 1, make_table(make_column("B", ["b"])))

        with patch.object(Kernel, "render", return_value=None):
            self._execute(workflow)
            Kernel.render.assert_not_called()

    @patch.object(rabbitmq, "send_update_to_workflow_clients", fake_send)
    def test_resume_without_rerunning_unneeded_renders(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        create_module_zipfile(
            # If this runs on step1, it'll return pd.DataFrame().
            # If this runs on step2, it'll return step1-output * 2.
            # ... step2's output depends on whether we run this on
            # step1.
            "mod",
            spec_kwargs={"loads_data": True},
            python_code="def render(table, params): return table * 2",
        )

        # step1: has a valid, cached result
        step1 = tab.steps.create(
            order=0,
            slug="step-1",
            last_relevant_delta_id=1,
            module_id_name="mod",
        )
        write_to_rendercache(workflow, step1, 1, make_table(make_column("A", [1])))

        # step2: has no cached result (must be rendered)
        step2 = tab.steps.create(
            order=1,
            slug="step-2",
            last_relevant_delta_id=1,
            module_id_name="mod",
        )

        self._execute(workflow)

        step2.refresh_from_db()
        with open_cached_render_result(step2.cached_render_result) as actual:
            assert_arrow_table_equals(actual.table, make_table(make_column("A", [2])))

    @patch.object(rabbitmq, "send_update_to_workflow_clients", fake_send)
    @patch("renderer.notifications.email_output_delta")
    def test_email_delta(self, email):
        user = create_test_user()
        workflow = Workflow.create_and_init(owner_id=user.id)
        tab = workflow.tabs.create(position=0)
        create_module_zipfile(
            "mod",
            spec_kwargs={"loads_data": True},
            python_code='import pandas as pd\ndef render(table, params): return pd.DataFrame({"A": [2]})',
        )
        step = tab.steps.create(
            order=0,
            slug="step-1",
            last_relevant_delta_id=2,
            module_id_name="mod",
            notifications=True,
        )
        # stale
        write_to_rendercache(workflow, step, 1, make_table(make_column("A", [1])))

        self._execute(workflow)

        email.assert_called()

    @patch.object(rabbitmq, "send_update_to_workflow_clients", fake_send)
    @patch("renderer.notifications.email_output_delta")
    def test_email_no_delta_when_not_changed(self, email):
        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        create_module_zipfile(
            "mod",
            spec_kwargs={"loads_data": True},
            python_code='import pandas as pd\ndef render(table, params): return pd.DataFrame({"A": [1]})',
        )
        step = tab.steps.create(
            order=0,
            slug="step-1",
            last_relevant_delta_id=2,
            module_id_name="mod",
            notifications=True,
        )
        # stale, same result
        write_to_rendercache(workflow, step, 1, make_table(make_column("A", [1])))

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
        create_module_zipfile(
            "mod",
            spec_kwargs={"loads_data": True},
            python_code='import pandas as pd\ndef render(table, params): return pd.DataFrame({"A": [1]})',
        )
        tab.steps.create(
            order=0,
            slug="step-1",
            module_id_name="mod",
            notifications=True,
        )

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
