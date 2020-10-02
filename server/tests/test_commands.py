import asyncio
from unittest.mock import patch
from cjwstate.models import Delta, Tab, Workflow, Step

# We'll use ChangeWorkflowTitleCommand and ChangeStepNotes as "canonical"
# deltas -- one requiring Step, one not.
from cjwstate import commands
from cjwstate.models.commands import (
    ChangeWorkflowTitleCommand,
    ChangeStepNotesCommand,
    AddTabCommand,
)
from cjwstate.tests.utils import DbTestCase


future_none = asyncio.Future()
future_none.set_result(None)


@patch.object(commands, "queue_render", lambda *x: future_none)
@patch.object(commands, "websockets_notify", lambda *x: future_none)
class DeltaTest(DbTestCase):
    def test_delete_orphans(self):
        workflow = Workflow.create_and_init()

        self.run_with_async_db(
            commands.do(
                ChangeWorkflowTitleCommand, workflow_id=workflow.id, new_value="1"
            )
        )
        delta2 = self.run_with_async_db(
            commands.do(
                ChangeWorkflowTitleCommand, workflow_id=workflow.id, new_value="2"
            )
        )
        delta3 = self.run_with_async_db(
            commands.do(
                ChangeWorkflowTitleCommand, workflow_id=workflow.id, new_value="3"
            )
        )
        self.run_with_async_db(commands.undo(delta3))
        self.run_with_async_db(commands.undo(delta2))
        # Create a new delta ... making delta2 and delta3 obsolete
        self.run_with_async_db(
            commands.do(
                ChangeWorkflowTitleCommand, workflow_id=workflow.id, new_value="4"
            )
        )

        with self.assertRaises(Delta.DoesNotExist):
            delta2.refresh_from_db()
        with self.assertRaises(Delta.DoesNotExist):
            delta3.refresh_from_db()

    def test_delete_orphans_does_not_delete_new_tab(self):
        """
        Don't delete a new AddTabCommand's new orphan Tab during creation.

        We delete orphans Deltas during creation, and we should delete their
        Tabs/Steps. But we shouldn't delete _new_ Tabs/Steps. (We need
        to order creation and deletion carefully to avoid doing so.)
        """
        workflow = Workflow.create_and_init()

        # Create a soft-deleted Tab in an orphan Delta (via AddTabCommand)
        delta1 = self.run_with_async_db(
            commands.do(
                AddTabCommand, workflow_id=workflow.id, slug="tab-2", name="name-2"
            )
        )
        self.run_with_async_db(commands.undo(delta1))

        # Now create a new Tab in a new Delta. This will delete delta1, and it
        # _should_ delete `tab-2`.
        self.run_with_async_db(
            commands.do(
                AddTabCommand, workflow_id=workflow.id, slug="tab-3", name="name-3"
            )
        )

        with self.assertRaises(Tab.DoesNotExist):
            delta1.tab.refresh_from_db()  # orphan tab was deleted
        with self.assertRaises(Delta.DoesNotExist):
            delta1.refresh_from_db()

    def test_delete_ignores_other_workflows(self):
        workflow = Workflow.create_and_init()
        workflow2 = Workflow.create_and_init()  # ignore me!

        # Create a delta we want to delete
        delta = self.run_with_async_db(
            commands.do(
                ChangeWorkflowTitleCommand, workflow_id=workflow.id, new_value="1"
            )
        )

        # Create deltas on workflow2 that we _don't_ want to delete
        delta2 = self.run_with_async_db(
            commands.do(
                ChangeWorkflowTitleCommand, workflow_id=workflow2.id, new_value="1"
            )
        )

        self.run_with_async_db(commands.undo(delta))  # fix workflow.last_delta_id
        delta.delete_with_successors()
        workflow.delete_orphan_soft_deleted_models()

        delta2.refresh_from_db()  # do not crash

    def test_delete_deletes_soft_deleted_step(self):
        workflow = Workflow.create_and_init()
        # Here's a soft-deleted module
        step = workflow.tabs.first().steps.create(
            order=0, slug="step-1", module_id_name="foo", is_deleted=True
        )

        delta = self.run_with_async_db(
            commands.do(
                ChangeWorkflowTitleCommand, workflow_id=workflow.id, new_value="1"
            )
        )
        self.run_with_async_db(commands.undo(delta))  # fix workflow.last_delta_id
        delta.delete_with_successors()
        workflow.delete_orphan_soft_deleted_models()

        with self.assertRaises(Step.DoesNotExist):
            step.refresh_from_db()

    def test_delete_deletes_soft_deleted_tab(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.create(position=1, is_deleted=True)
        # create a step -- it needs to be deleted, too!
        step = tab.steps.create(
            order=0, slug="step-1", module_id_name="foo", is_deleted=True
        )

        delta = self.run_with_async_db(
            commands.do(
                ChangeWorkflowTitleCommand, workflow_id=workflow.id, new_value="1"
            )
        )
        self.run_with_async_db(commands.undo(delta))  # fix workflow.last_delta_id
        delta.delete_with_successors()
        workflow.delete_orphan_soft_deleted_models()

        with self.assertRaises(Step.DoesNotExist):
            step.refresh_from_db()
        with self.assertRaises(Tab.DoesNotExist):
            tab.refresh_from_db()

    def test_delete_protects_non_deleted_step(self):
        workflow = Workflow.create_and_init()
        # Here's a soft-deleted module
        step = workflow.tabs.first().steps.create(
            order=0, slug="step-1", module_id_name="foo", is_deleted=False
        )

        # delete a delta
        delta = self.run_with_async_db(
            commands.do(
                ChangeWorkflowTitleCommand, workflow_id=workflow.id, new_value="1"
            )
        )
        self.run_with_async_db(commands.undo(delta))  # fix workflow.last_delta_id
        delta.delete_with_successors()
        workflow.delete_orphan_soft_deleted_models()

        step.refresh_from_db()  # no DoesNotExist: it's not deleted

    def test_delete_protects_soft_deleted_step_with_reference(self):
        workflow = Workflow.create_and_init()
        # Here's a soft-deleted module
        step = workflow.tabs.first().steps.create(
            order=0, slug="step-1", module_id_name="foo", is_deleted=True
        )

        # "protect" it: here's a delta we _aren't_ deleting
        self.run_with_async_db(
            commands.do(
                ChangeStepNotesCommand,
                workflow_id=workflow.id,
                step=step,
                new_value="1",
            )
        )

        # now delete a delta
        delta = self.run_with_async_db(
            commands.do(
                ChangeWorkflowTitleCommand, workflow_id=workflow.id, new_value="1"
            )
        )
        self.run_with_async_db(commands.undo(delta))  # fix workflow.last_delta_id
        delta.delete_with_successors()
        workflow.delete_orphan_soft_deleted_models()

        step.refresh_from_db()  # no DoesNotExist -- a delta depends on it

    def test_delete_scopes_step_delete_by_workflow(self):
        workflow = Workflow.create_and_init()
        workflow2 = Workflow.create_and_init()
        # Here's a soft-deleted module on workflow2. Nothing references it. It
        # "shouldn't" exist.
        step = workflow2.tabs.first().steps.create(
            order=0, slug="step-1", module_id_name="foo", is_deleted=True
        )

        # now delete a delta on workflow1
        delta = self.run_with_async_db(
            commands.do(
                ChangeWorkflowTitleCommand, workflow_id=workflow.id, new_value="1"
            )
        )
        self.run_with_async_db(commands.undo(delta))  # fix workflow.last_delta_id
        delta.delete_with_successors()
        workflow.delete_orphan_soft_deleted_models()

        step.refresh_from_db()  # no DoesNotExist: leave workflow2 alone

    def test_delete_scopes_tab_delete_by_workflow(self):
        workflow = Workflow.create_and_init()
        workflow2 = Workflow.create_and_init()
        # Here's a soft-deleted module on workflow2. Nothing references it. It
        # "shouldn't" exist.
        tab = workflow2.tabs.create(position=1)

        # now delete a delta on workflow1
        delta = self.run_with_async_db(
            commands.do(
                ChangeWorkflowTitleCommand, workflow_id=workflow.id, new_value="1"
            )
        )
        self.run_with_async_db(commands.undo(delta))  # fix workflow.last_delta_id
        delta.delete_with_successors()
        workflow.delete_orphan_soft_deleted_models()

        tab.refresh_from_db()  # no DoesNotExist: leave workflow2 alone
