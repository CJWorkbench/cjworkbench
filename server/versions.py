from django.db.models import F
from cjworkbench.sync import database_sync_to_async
from cjwstate import commands
from cjwstate.models import Delta, Workflow
from cjwstate.models.commands import InitWorkflowCommand


@database_sync_to_async
def _load_last_delta(workflow_id: int) -> Delta:
    """
    Read the current Delta for a workflow from the database.

    Raise Delta.DoesNotExist if there is no next delta.
    """
    return Delta.objects.get(workflow_id=workflow_id, workflow__last_delta_id=F("id"))


@database_sync_to_async
def _load_next_delta(workflow_id: int) -> Delta:
    """
    Read (undone, not-applied) "next" Delta for a workflow from the database.

    Raise Delta.DoesNotExist if there is no next delta.
    """
    return Delta.objects.get(
        workflow_id=workflow_id, workflow__last_delta_id=F("prev_delta_id")
    )


async def WorkflowUndo(workflow_id: int):
    """
    Run commands.undo(workflow.last_delta).

    This may modify the passed `workflow`.
    """
    # TODO avoid race undoing the same delta twice (or make it a no-op)
    try:
        delta = await _load_last_delta(workflow_id)
    except Delta.DoesNotExist:
        return

    if not isinstance(delta, InitWorkflowCommand):
        await commands.undo(delta)  # uses cooperative_lock()


async def WorkflowRedo(workflow_id: int):
    """
    Run commands.redo(workflow.last_delta.next_delta), if there is one.

    The delta may modify the passed `workflow`.
    """
    # TODO avoid race redoing the same delta twice (or make it a no-op)
    try:
        delta = await _load_next_delta(workflow_id)
    except Delta.DoesNotExist:
        return

    await commands.redo(delta)  # uses cooperative_lock()
