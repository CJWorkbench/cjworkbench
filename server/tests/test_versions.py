import logging
from unittest.mock import patch
from cjwstate import commands
from cjwstate.models import Delta, ModuleVersion, Workflow
from cjwstate.models.commands import (
    AddModuleCommand,
    ChangeParametersCommand,
    ChangeWorkflowTitleCommand,
    ChangeStepNotesCommand,
)
from cjwstate.tests.utils import (
    DbTestCaseWithModuleRegistryAndMockKernel,
    create_module_zipfile,
)
from server.versions import WorkflowUndo, WorkflowRedo


async def async_noop(*args, **kwargs):
    pass


@patch.object(commands, "queue_render", async_noop)
@patch.object(commands, "websockets_notify", async_noop)
class VersionsTests(DbTestCaseWithModuleRegistryAndMockKernel):
    # Be careful, in these tests, not to run database queries in async blocks.

    def assertStepVersions(self, tab, expected_versions):
        result = list(tab.live_steps.values_list("last_relevant_delta_id", flat=True))
        self.assertEqual(result, expected_versions)

    # Many things tested here:
    #  - Undo with 0,1,2 commands in stack
    #  - Redo with 0,1,2 commands to redo
    #  - Start with 3 commands in stack, then undo, undo, new command -> blow
    #    away commands 2,3
    # Command types used here are arbitrary, but different so that we test
    # polymorphism
    def test_undo_redo(self):
        mz = create_module_zipfile(
            "loadsomething",
            spec_kwargs={"parameters": [{"id_name": "csv", "type": "string"}]},
        )
        self.kernel.migrate_params.side_effect = lambda m, p: p

        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()

        all_modules = tab.live_steps  # beginning state: nothing

        v0 = workflow.last_delta_id

        # Test undoing nothing at all. Should NOP
        self.run_with_async_db(WorkflowUndo(workflow.id))
        workflow.refresh_from_db()
        self.assertEqual(all_modules.count(), 0)
        self.assertEqual(workflow.last_delta_id, v0)

        # Add a module
        cmd1 = self.run_with_async_db(
            commands.do(
                AddModuleCommand,
                workflow_id=workflow.id,
                tab=tab,
                slug="step-1",
                module_id_name="loadsomething",
                position=0,
                param_values={},
            )
        )
        v1 = cmd1.id
        workflow.refresh_from_db()
        self.assertEqual(all_modules.count(), 1)
        self.assertGreater(v1, v0)
        self.assertEqual(workflow.last_delta_id, v1)
        self.assertStepVersions(tab, [v1])

        # Undo, ensure we are back at start
        self.run_with_async_db(WorkflowUndo(workflow.id))
        workflow.refresh_from_db()
        self.assertEqual(all_modules.count(), 0)
        self.assertEqual(workflow.last_delta_id, v0)
        self.assertStepVersions(tab, [])

        # Redo, ensure we are back at v1
        self.run_with_async_db(WorkflowRedo(workflow.id))
        workflow.refresh_from_db()
        self.assertEqual(all_modules.count(), 1)
        self.assertEqual(workflow.last_delta_id, v1)
        self.assertStepVersions(tab, [v1])

        # Change a parameter
        with self.assertLogs(level=logging.INFO):
            cmd2 = self.run_with_async_db(
                commands.do(
                    ChangeParametersCommand,
                    workflow_id=workflow.id,
                    step=tab.live_steps.first(),
                    new_values={"csv": "some value"},
                )
            )
        v2 = cmd2.id
        workflow.refresh_from_db()
        self.assertEqual(tab.live_steps.first().params["csv"], "some value")
        self.assertEqual(workflow.last_delta_id, v2)
        self.assertGreater(v2, v1)
        self.assertStepVersions(tab, [v2])

        # Undo parameter change
        with self.assertLogs(level=logging.INFO):
            self.run_with_async_db(WorkflowUndo(workflow.id))
        workflow.refresh_from_db()
        self.assertEqual(workflow.last_delta_id, v1)
        self.assertEqual(tab.live_steps.first().params["csv"], "")
        self.assertStepVersions(tab, [v1])

        # Redo
        with self.assertLogs(level=logging.INFO):
            self.run_with_async_db(WorkflowRedo(workflow.id))
        workflow.refresh_from_db()
        self.assertEqual(workflow.last_delta_id, v2)
        self.assertEqual(tab.live_steps.first().params["csv"], "some value")
        self.assertStepVersions(tab, [v2])

        # Redo again should do nothing
        self.run_with_async_db(WorkflowRedo(workflow.id))
        workflow.refresh_from_db()
        self.assertEqual(workflow.last_delta_id, v2)
        self.assertEqual(tab.live_steps.first().params["csv"], "some value")
        self.assertStepVersions(tab, [v2])

        # Add one more command so the stack is 3 deep
        cmd3 = self.run_with_async_db(
            commands.do(
                ChangeWorkflowTitleCommand,
                workflow_id=workflow.id,
                new_value="New Title",
            )
        )
        v3 = cmd3.id
        self.assertGreater(v3, v2)
        self.assertStepVersions(tab, [v2])

        # Undo twice
        self.run_with_async_db(WorkflowUndo(workflow.id))
        workflow.refresh_from_db()
        self.assertEqual(workflow.last_delta, cmd2)
        self.assertStepVersions(tab, [v2])
        with self.assertLogs(level=logging.INFO):
            self.run_with_async_db(WorkflowUndo(workflow.id))
        workflow.refresh_from_db()
        self.assertEqual(workflow.last_delta, cmd1)
        self.assertStepVersions(tab, [v1])

        # Redo twice
        with self.assertLogs(level=logging.INFO):
            self.run_with_async_db(WorkflowRedo(workflow.id))
        workflow.refresh_from_db()
        self.assertEqual(workflow.last_delta, cmd2)
        self.assertStepVersions(tab, [v2])
        self.run_with_async_db(WorkflowRedo(workflow.id))
        workflow.refresh_from_db()
        self.assertEqual(workflow.last_delta, cmd3)
        self.assertStepVersions(tab, [v2])

        # Undo again to get to a place where we have two commands to redo
        self.run_with_async_db(WorkflowUndo(workflow.id))
        with self.assertLogs(level=logging.INFO):
            self.run_with_async_db(WorkflowUndo(workflow.id))
        workflow.refresh_from_db()
        self.assertEqual(workflow.last_delta, cmd1)

        # Now add a new command. It should remove cmd2, cmd3 from the redo
        # stack and delete them from the db
        step = all_modules.first()
        cmd4 = self.run_with_async_db(
            commands.do(
                ChangeStepNotesCommand,
                workflow_id=workflow.id,
                step=step,
                new_value="Note of no note",
            )
        )
        v4 = cmd4.id
        workflow.refresh_from_db()
        self.assertEqual(workflow.last_delta_id, v4)
        self.assertEqual(
            set(Delta.objects.values_list("id", flat=True)), {v0, v1, v4}
        )  # v2, v3 deleted

        # Undo back to start, then add a command, ensure it deletes dangling
        # commands (tests an edge case in Delta.save)
        self.run_with_async_db(WorkflowUndo(workflow.id))
        workflow.refresh_from_db()
        self.assertEqual(workflow.last_delta_id, v1)
        cmd5 = self.run_with_async_db(
            commands.do(
                ChangeStepNotesCommand,
                workflow_id=workflow.id,
                step=cmd1.step,
                new_value="Note of some note",
            )
        )
        v5 = cmd5.id
        workflow.refresh_from_db()
        self.assertEqual(workflow.last_delta_id, v5)
        self.assertEqual(
            set(Delta.objects.values_list("id", flat=True)), {v0, v1, v5}
        )  # v1, v4 deleted
        self.assertStepVersions(tab, [v1])
