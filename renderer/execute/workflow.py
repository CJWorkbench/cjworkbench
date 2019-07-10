from typing import Dict, List, Optional, Tuple
from cjworkbench.sync import database_sync_to_async
from cjworkbench.types import StepResultShape
from server.models import Workflow
from server.models.param_dtype import ParamDType
from .tab import ExecuteStep, TabFlow, execute_tab_flow
from .types import UnneededExecution


@database_sync_to_async
def _load_tab_flows(workflow: Workflow, delta_id: int) -> List[TabFlow]:
    """
    Query `workflow` for each tab's `TabFlow` (ordered by tab position).
    """
    ret = []
    with workflow.cooperative_lock():  # reloads workflow
        if workflow.last_delta_id != delta_id:
            raise UnneededExecution

        for tab in workflow.live_tabs.all():
            steps = [
                ExecuteStep(
                    wfm,
                    (
                        wfm.module_version.param_schema
                        if wfm.module_version is not None
                        else ParamDType.Dict({})
                    ),
                    wfm.get_params(),
                )
                for wfm in tab.live_wf_modules.all()
            ]
            ret.append(TabFlow(tab, steps))
    return ret


def partition_ready_and_dependent(
    flows: List[TabFlow]
) -> Tuple[List[TabFlow], List[TabFlow]]:
    """
    Find `(ready_flows, dependent_flows)` from `flows`.

    "Ready" TabFlows are TabFlows that don't depend on not-yet-rendered Tabs.

    "Dependent" TabFlows are TabFlows that have one or more Tab parameters that
    refer to Tabs that haven't been rendered.

    Tab parameters with no value -- and Tab parameters that point to
    nonexistent Tabs -- are treated as "ready". (This lets us optimize
    cleverly: we don't even need to know the list of already-rendered tabs to
    know whether a TabFlow is ready.)
    """
    pending_tab_slugs = frozenset(flow.tab_slug for flow in flows)

    ready = []
    dependent = []
    for flow in flows:
        if pending_tab_slugs & flow.input_tab_slugs:
            dependent.append(flow)
        else:
            ready.append(flow)
    return (ready, dependent)


async def execute_workflow(workflow: Workflow, delta_id: int) -> None:
    """
    Ensure all `workflow.tabs[*].live_wf_modules` cache fresh render results.

    Raise UnneededExecution if the inputs become stale (at which point we don't
    care about results any more).

    WEBSOCKET NOTES: each wf_module is executed in turn. After each execution,
    we notify clients of its new columns and status.
    """
    # raises UnneededExecution
    pending_tab_flows = await _load_tab_flows(workflow, delta_id)

    # tab_shapes: keep track of outputs of each tab. (Outputs are used as
    # inputs into other tabs.) Before render begins, all outputs are `None`.
    # We'll execute tabs dependencies-first; if a WfModule depends on a
    # `tab_shape` we haven't rendered yet, that's because it _couldn't_ be
    # rendered first -- prompting a `TabCycleError`.
    #
    # `tab_shapes.keys()` returns tab slugs in the Workflow's tab order -- that
    # is, the order the user determines.
    tab_shapes: Dict[str, Optional[StepResultShape]] = dict(
        (flow.tab_slug, None) for flow in pending_tab_flows
    )

    # Execute one tab_flow at a time.
    #
    # We don't hold a DB lock throughout the loop: the loop can take a long
    # time; it might be run multiple times simultaneously (even on different
    # computers); and `await` doesn't work with locks.

    while pending_tab_flows:
        ready_flows, dependent_flows = partition_ready_and_dependent(pending_tab_flows)

        if not ready_flows:
            # All flows are dependent -- meaning they all have cycles. Execute
            # them last; they can detect their cycles through `tab_shapes`.
            break

        for tab_flow in ready_flows:
            result = await execute_tab_flow(workflow, tab_flow, tab_shapes)
            tab_shape = StepResultShape(result.status, result.table_shape)
            del result  # recover ram
            tab_shapes[tab_flow.tab_slug] = tab_shape

        pending_tab_flows = dependent_flows  # iterate

    # Now, `pending_tab_flows` only contains flows with cycles. Execute them,
    # but don't update `tab_shapes` because none of them should see the output
    # from any other. (If tab1 and tab 2 depend on each other, they should both
    # have the same error: "Cycle"; their order of execution shouldn't matter.)
    for tab_flow in pending_tab_flows:
        await execute_tab_flow(workflow, tab_flow, tab_shapes)
