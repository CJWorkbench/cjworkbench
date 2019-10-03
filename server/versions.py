from typing import Optional
from cjworkbench.sync import database_sync_to_async
from cjwstate import commands
from cjwstate.models import Delta, Workflow
from cjwstate.models.commands import InitWorkflowCommand


@database_sync_to_async
def _load_last_delta(workflow: Workflow) -> Delta:
    """
    Read a Delta from the database.
    """
    delta = workflow.last_delta

    if delta is None:
        raise RuntimeError("Workflow %d has no deltas", workflow.id)

    # Deltas write to their `self.workflow`. Make them read/write the Workflow
    # _we_ see instead of querying their own `workflow` from the database.
    delta.workflow = workflow
    return delta


@database_sync_to_async
def _load_next_delta(workflow: Workflow) -> Optional[Delta]:
    """
    Read a Delta from the database.
    """
    prev_delta = workflow.last_delta

    if not prev_delta:
        raise RuntimeError("Workflow %d has no deltas", workflow.id)

    try:
        delta = prev_delta.next_delta
    except Delta.DoesNotExist:
        return None

    # Deltas write to their `self.workflow`. Make them read/write the Workflow
    # _we_ see instead of querying their own `workflow` from the database.
    delta.workflow = workflow
    return delta


async def WorkflowUndo(workflow):
    """
    Run commands.undo(workflow.last_delta).

    This may modify the passed `workflow`.
    """
    # TODO avoid race undoing the same delta twice (or make it a no-op)
    delta = await _load_last_delta(workflow)

    if not isinstance(delta, InitWorkflowCommand):
        await commands.undo(delta)  # uses cooperative_lock()


async def WorkflowRedo(workflow):
    """
    Run commands.redo(workflow.last_delta.next_delta), if there is one.

    The delta may modify the passed `workflow`.
    """
    # TODO avoid race redoing the same delta twice (or make it a no-op)
    delta = await _load_next_delta(workflow)

    if not delta:
        return

    await commands.redo(delta)  # uses cooperative_lock()
