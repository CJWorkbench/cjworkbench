from typing import Set
from channels.db import database_sync_to_async
from server.models import Workflow
from .tab import TabFlow, execute_tab_flow
from .types import UnneededExecution


@database_sync_to_async
def _load_tab_flows(workflow: Workflow, delta_id: int) -> Set[TabFlow]:
    """
    Query `workflow` each tab's `TabFlow`.
    """
    ret = []
    with workflow.cooperative_lock():  # reloads workflow
        if workflow.last_delta_id != delta_id:
            raise UnneededExecution

        for tab in workflow.live_tabs.all():
            steps = [(wfm, wfm.get_params())
                     for wfm in tab.live_wf_modules.all()]
            ret.append(TabFlow(tab, steps))
    return ret


async def execute_workflow(workflow: Workflow, delta_id: int) -> None:
    """
    Ensure all `workflow.tabs[*].live_wf_modules` cache fresh render results.

    Raise UnneededExecution if the inputs become stale (at which point we don't
    care about results any more).

    WEBSOCKET NOTES: each wf_module is executed in turn. After each execution,
    we notify clients of its new columns and status.
    """
    # raises UnneededExecution
    tab_flows = await _load_tab_flows(workflow, delta_id)

    # Execute one tab_flow at a time.
    #
    # We don't hold any lock throughout the loop: the loop can take a long
    # time; it might be run multiple times simultaneously (even on
    # different computers); and `await` doesn't work with locks.
    for tab_flow in tab_flows:
        await execute_tab_flow(workflow, tab_flow)
