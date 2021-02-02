import datetime
from typing import Optional

from freezegun import freeze_time

from cjwstate import commands
from cjwstate.models import Delta, Workflow

# Use SetWorkflowTitle and AddStep as "canonical" deltas -- one
# requiring Step, one not.
from cjwstate.models.commands import SetWorkflowTitle, AddStep
from cjwstate.tests.utils import (
    DbTestCaseWithModuleRegistryAndMockKernel,
    create_module_zipfile,
)
from cjworkbench.tests.utils import DbTestCase

from cron.deltadeleter import delete_workflow_stale_deltas

# sync functions to build undo history in the database without RabbitMQ
#
# do(), redo() and undo() work the same way as the real ones
def do(cls, workflow_id: int, **kwargs) -> Optional[Delta]:
    delta, _, __ = commands._first_forward_and_save_returning_clientside_update.func(
        cls, workflow_id, **kwargs
    )
    return delta


redo = commands._call_forward_and_load_clientside_update.func
undo = commands._call_backward_and_load_clientside_update.func


def be_paranoid_and_assert_commands_apply(workflow: Workflow) -> None:
    """Run some excessive tests.

    This made sense [2021-02-02] when we first implemented this feature. But has
    it ever caught an error? It didn't on 2021-02-02 when it was added to every
    test.
    """
    workflow.refresh_from_db()
    name1 = workflow.name
    delta = do(SetWorkflowTitle, workflow.id, new_value="paranoid")
    workflow.refresh_from_db()
    assert workflow.last_delta_id == delta.id
    assert workflow.name == "paranoid"
    undo(workflow.id)
    workflow.refresh_from_db()
    assert workflow.name == name1


class DeleteWorkflowStaleDeltasTest(DbTestCaseWithModuleRegistryAndMockKernel):
    def test_keep_recent_done_deltas(self):
        workflow = Workflow.create_and_init()
        with freeze_time("2020-02-02"):
            do(SetWorkflowTitle, workflow.id, new_value="foo")
            do(SetWorkflowTitle, workflow.id, new_value="bar")
        delete_workflow_stale_deltas(workflow.id, datetime.datetime(2020, 1, 1))
        self.assertEqual(workflow.deltas.count(), 2)

        be_paranoid_and_assert_commands_apply(workflow)

    def test_delete_stale_done_deltas_before_fresh(self):
        workflow = Workflow.create_and_init()
        with freeze_time("1970-01-01"):
            do(SetWorkflowTitle, workflow.id, new_value="foo")
            do(SetWorkflowTitle, workflow.id, new_value="bar")
        with freeze_time("2020-02-02"):
            delta3 = do(SetWorkflowTitle, workflow.id, new_value="baz")

        delete_workflow_stale_deltas(workflow.id, datetime.datetime(2020, 1, 1))

        # We delete up to the latest fresh one....
        self.assertEqual(workflow.deltas.first().id, delta3.id)

        be_paranoid_and_assert_commands_apply(workflow)

    def test_delete_stale_done_deltas_until_no_deltas_remain(self):
        workflow = Workflow.create_and_init()
        with freeze_time("1970-01-01"):
            do(SetWorkflowTitle, workflow.id, new_value="foo")
            do(SetWorkflowTitle, workflow.id, new_value="bar")

        delete_workflow_stale_deltas(workflow.id, datetime.datetime(2020, 1, 1))

        self.assertEqual(workflow.deltas.count(), 0)

        be_paranoid_and_assert_commands_apply(workflow)

    def test_delete_fresh_done_delta_before_stale_done_delta(self):
        # In case clocks are out of sync or there's corrupt data
        #
        # We don't care whether we delete both or keep both; just that we never
        # delete from the middle.
        workflow = Workflow.create_and_init()
        with freeze_time("2020-02-02"):
            do(SetWorkflowTitle, workflow.id, new_value="foo")
        with freeze_time("1970-01-01"):
            # second Delta happened "before" the first!
            do(SetWorkflowTitle, workflow.id, new_value="bar")
        with freeze_time("2020-02-02"):
            delta3 = do(SetWorkflowTitle, workflow.id, new_value="baz")

        delete_workflow_stale_deltas(workflow.id, datetime.datetime(2020, 1, 1))

        # We delete up to the latest fresh one....
        self.assertEqual(workflow.deltas.first().id, delta3.id)

        be_paranoid_and_assert_commands_apply(workflow)

    def test_keep_recent_undone_deltas(self):
        workflow = Workflow.create_and_init()
        with freeze_time("1970-01-01"):
            do(SetWorkflowTitle, workflow.id, new_value="foo")
            do(SetWorkflowTitle, workflow.id, new_value="bar")
        with freeze_time("2020-02-02"):
            # Updates their last_applied_at
            undo(workflow.id)
            undo(workflow.id)
        delete_workflow_stale_deltas(workflow.id, datetime.datetime(2020, 1, 1))
        self.assertEqual(workflow.deltas.count(), 2)

        be_paranoid_and_assert_commands_apply(workflow)

    def test_delete_stale_undone_deltas(self):
        workflow = Workflow.create_and_init()
        with freeze_time("1970-01-01"):
            do(SetWorkflowTitle, workflow.id, new_value="foo")
            do(SetWorkflowTitle, workflow.id, new_value="bar")
            undo(workflow.id)
            undo(workflow.id)
        delete_workflow_stale_deltas(workflow.id, datetime.datetime(2020, 1, 1))
        self.assertEqual(workflow.deltas.count(), 0)

        be_paranoid_and_assert_commands_apply(workflow)

    def test_delete_stale_undone_deltas_after_fresh(self):
        workflow = Workflow.create_and_init()
        with freeze_time("1970-01-01"):
            delta1 = do(SetWorkflowTitle, workflow.id, new_value="foo")
            do(SetWorkflowTitle, workflow.id, new_value="bar")
            undo(workflow.id)
        with freeze_time("2020-02-02"):
            undo(workflow.id)  # undo delta1 recently
        delete_workflow_stale_deltas(workflow.id, datetime.datetime(2020, 1, 1))
        self.assertEqual(
            list(workflow.deltas.values_list("id", flat=True)), [delta1.id]
        )

        be_paranoid_and_assert_commands_apply(workflow)

    def test_delete_fresh_undone_delta_after_stale(self):
        # In case clocks are out of sync or there's corrupt data
        #
        # We don't care whether we delete both or keep both; just that we never
        # delete from the middle.
        workflow = Workflow.create_and_init()
        with freeze_time("1970-01-01"):
            delta1 = do(SetWorkflowTitle, workflow.id, new_value="foo")
            do(SetWorkflowTitle, workflow.id, new_value="bar")
            do(SetWorkflowTitle, workflow.id, new_value="baz")
        with freeze_time("2020-02-02"):
            undo(workflow.id)  # undone recently
        with freeze_time("1970-01-01"):
            undo(workflow.id)  # corrupt! undone long ago
        with freeze_time("2020-02-02"):
            undo(workflow.id)  # undone recently

        delete_workflow_stale_deltas(workflow.id, datetime.datetime(2020, 1, 1))

        # We delete up to the first stale one
        self.assertEqual(workflow.deltas.first().id, delta1.id)

        be_paranoid_and_assert_commands_apply(workflow)

    def test_delete_all_done_and_undone_deltas(self):
        workflow = Workflow.create_and_init()
        with freeze_time("1970-01-01"):
            delta1 = do(SetWorkflowTitle, workflow.id, new_value="foo")
            do(SetWorkflowTitle, workflow.id, new_value="bar")
            do(SetWorkflowTitle, workflow.id, new_value="baz")
            do(SetWorkflowTitle, workflow.id, new_value="moo")
            undo(workflow.id)
            undo(workflow.id)

        delete_workflow_stale_deltas(workflow.id, datetime.datetime(2020, 1, 1))

        self.assertEqual(workflow.deltas.count(), 0)

        be_paranoid_and_assert_commands_apply(workflow)

    def test_keep_done_and_undone_deltas_between_stale_ones(self):
        workflow = Workflow.create_and_init()
        # delta1 and delta4 are from long ago. delta2 and delta3 have been
        # used recently.
        with freeze_time("1970-01-01"):
            do(SetWorkflowTitle, workflow.id, new_value="foo")
            delta2 = do(SetWorkflowTitle, workflow.id, new_value="bar")
            delta3 = do(SetWorkflowTitle, workflow.id, new_value="baz")
            do(SetWorkflowTitle, workflow.id, new_value="moo")
            undo(workflow.id)
        with freeze_time("2020-02-02"):
            undo(workflow.id)
            undo(workflow.id)
            redo(workflow.id)

        delete_workflow_stale_deltas(workflow.id, datetime.datetime(2020, 1, 1))

        self.assertEqual(
            list(workflow.deltas.values_list("id", flat=True)), [delta2.id, delta3.id]
        )

        be_paranoid_and_assert_commands_apply(workflow)

    def test_delete_orphan_soft_deleted_steps(self):
        mod = create_module_zipfile("mod")
        workflow = Workflow.create_and_init()
        with freeze_time("1970-01-01"):
            do(SetWorkflowTitle, workflow.id, new_value="foo")
            do(
                AddStep,
                workflow.id,
                tab=workflow.tabs.first(),
                slug="step-2",
                module_id_name="mod",
                position=0,
                param_values={},
            )
            undo(workflow.id)
        self.assertEqual(workflow.tabs.first().steps.count(), 1)  # soft-deleted

        delete_workflow_stale_deltas(workflow.id, datetime.datetime(2020, 1, 1))

        self.assertEqual(workflow.tabs.first().steps.count(), 0)  # hard-deleted
