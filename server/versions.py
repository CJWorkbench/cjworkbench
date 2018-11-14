from typing import Optional
from channels.db import database_sync_to_async
from server.models import Delta, Workflow


@database_sync_to_async
def _load_last_delta(workflow: Workflow) -> Optional[Delta]:
    """
    Read a Delta from the database.

    TODO currently the return value may be `None`. This is a historical quirk.
    All new Workflows have at least one Delta (an InitWorkflowCommand), and we
    should migrate old Workflows as well. [2018-11-14] we haven't yet.
    """
    delta = workflow.last_delta

    if not delta:
        return None

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
        # TODO force every workflow to have at least one Delta.
        #
        # [2018-11-14] for now we don't have that guarantee. So look for a
        # Delta on the workflow that has no prev_delta: that's the "next" one.
        delta = Delta.objects.filter(workflow=workflow,
                                     prev_delta_id=None).first()

        if not delta:
            return None
    else:
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
    Run workflow.last_delta.backward().

    The delta may modify the passed `workflow`.
    """
    # TODO avoid race undoing the same delta twice (or make it a no-op)
    delta = await _load_last_delta(workflow)

    if not delta:
        return  # TODO nix the no-delta-in-Workflow case

    await delta.backward()  # Delta uses cooperative lock


async def WorkflowRedo(workflow):
    """
    Run workflow.last_delta.next_delta.forward(), if there is a next delta.

    The delta may modify the passed `workflow`.
    """
    # TODO avoid race redoing the same delta twice (or make it a no-op)
    delta = await _load_next_delta(workflow)

    if not delta:
        return

    await delta.forward()  # Delta uses cooperative lock
