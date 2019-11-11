import logging
from typing import Any, Dict, List, Optional, Tuple
from cjworkbench.sync import database_sync_to_async
from cjwkernel.chroot import EDITABLE_CHROOT
from cjwkernel.errors import ModuleError
from cjwkernel.param_dtype import ParamDType
from cjwkernel.types import RenderResult, Tab
from cjwstate.models import WfModule, Workflow
from cjwstate.params import get_migrated_params
from .tab import ExecuteStep, TabFlow, execute_tab_flow
from .types import UnneededExecution


logger = logging.getLogger(__name__)


def _get_migrated_params(wf_module: WfModule) -> Dict[str, Any]:
    """
    Build the Params dict which will be passed to render().

    Call LoadedModule.migrate_params() to ensure the params are up-to-date.

    On ModuleError or ValueError, log the error and return default params. This
    will render the "wrong" thing ... but the front-end should show the migrate
    error (as it's rendering the form) so users should figure out the problem.
    (What's the alternative? Abort the whole workflow render? We can't render
    _any_ module until we've migrated _all_ modules; and it's hard to imagine
    showing the user a huge, aborted render.)

    Assume we are called within a `workflow.cooperative_lock()`.
    """
    module_version = wf_module.module_version

    if module_version is None:
        # This is a deleted module. Renderer will pass the input through to
        # the output.
        return {}

    try:
        result = get_migrated_params(wf_module)
    except ModuleError:
        # LoadedModule logged this error; no need to log it again.
        return module_version.param_schema.coerce(None)

    # Is the module buggy? It might be. Log that error, and return a valid
    # set of params anyway -- even if it isn't the params the user wants.
    try:
        module_version.param_schema.validate(result)
        return result
    except ValueError as err:
        logger.exception(
            "%s.migrate_params() gave wrong retval: %s",
            module_version.id_name,
            str(err),
        )
        return module_version.param_schema.coerce(result)


@database_sync_to_async
def _load_tab_flows(workflow: Workflow, delta_id: int) -> List[TabFlow]:
    """
    Query `workflow` for each tab's `TabFlow` (ordered by tab position).

    Raise `ModuleError` or `ValueError` if migrate_params() fails. Failed
    migration means the whole execute can't happen.
    """
    ret = []
    with workflow.cooperative_lock():  # reloads workflow
        if workflow.last_delta_id != delta_id:
            raise UnneededExecution

        for tab_model in workflow.live_tabs.all():
            steps = [
                ExecuteStep(
                    wfm,
                    (
                        wfm.module_version.param_schema
                        if wfm.module_version is not None
                        else ParamDType.Dict({})
                    ),
                    # We need to invoke the kernel and migrate _all_ modules'
                    # params (WfModule.get_params), because we can only check
                    # for tab cycles after migrating (and before calling any
                    # render()).
                    _get_migrated_params(wfm),
                )
                for wfm in tab_model.live_wf_modules.all()
            ]
            ret.append(TabFlow(Tab(tab_model.slug, tab_model.name), steps))
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
    tab_results: Dict[Tab, Optional[RenderResult]] = {
        flow.tab: None for flow in pending_tab_flows
    }
    output_paths = []

    # Execute one tab_flow at a time.
    #
    # We don't hold a DB lock throughout the loop: the loop can take a long
    # time; it might be run multiple times simultaneously (even on different
    # computers); and `await` doesn't work with locks.

    with EDITABLE_CHROOT.acquire_context() as chroot_context:
        with chroot_context.tempdir_context("render-") as basedir:

            async def execute_tab_flow_into_new_file(tab_flow: TabFlow) -> RenderResult:
                nonlocal workflow, tab_results, output_paths
                output_path = basedir / (
                    "tab-output-%s.arrow" % tab_flow.tab_slug.replace("/", "-")
                )
                return await execute_tab_flow(
                    chroot_context, workflow, tab_flow, tab_results, output_path
                )

            while pending_tab_flows:
                ready_flows, dependent_flows = partition_ready_and_dependent(
                    pending_tab_flows
                )

                if not ready_flows:
                    # All flows are dependent -- meaning they all have cycles. Execute
                    # them last; they can detect their cycles through `tab_results`.
                    break

                for tab_flow in ready_flows:
                    result = await execute_tab_flow_into_new_file(tab_flow)
                    tab_results[tab_flow.tab] = result

                pending_tab_flows = dependent_flows  # iterate

            # Now, `pending_tab_flows` only contains flows with cycles. Execute
            # them. No need to update `tab_results`: If tab1 and tab 2 depend on
            # each other, they should have the same error ("Cycle").
            for tab_flow in pending_tab_flows:
                await execute_tab_flow_into_new_file(tab_flow)
