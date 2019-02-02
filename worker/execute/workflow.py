from channels.db import database_sync_to_async
from server.models import Workflow
from .wf_module import execute_wfmodule


@database_sync_to_async
def _load_tabs_wf_modules_and_input(workflow: Workflow):
    """
    Queries for each tab's (stale_steps, input_cached_result_or_none).

    If all steps are up-to-date, returns ([], output_cached_result) for that
    tab. Yes, beware: if we aren't rendering, we return *output*, and if we are
    rendering we return *input*. This is convenient for the caller.

    If there's a race, the returned `stale_wf_modules` may be too short, and
    `input_table` may be wrong. That should be fine because `execute_wfmodule`
    will raise an exception before starting work.
    """
    with workflow.cooperative_lock():
        ret = []

        tabs = list(workflow.live_tabs)
        for tab in tabs:
            # 1. Load list of wf_modules
            wf_modules = list(tab.live_wf_modules)
            # ... including their cached results, if they're fresh
            cached_results = [wf_module.cached_render_result
                              for wf_module in wf_modules]

            # 2. Find index of first one that needs render
            try:
                index = cached_results.index(None)
            except ValueError:
                index = len(wf_modules)

            wf_modules_needing_render = wf_modules[index:]

            if not wf_modules_needing_render:
                # We're up to date! Skip the entire tab.
                continue

            # 4. Load input
            if index == 0:
                prev_result = None
            else:
                prev_result = cached_results[index - 1]

            ret.append((wf_modules_needing_render, prev_result))

        return ret


async def execute_workflow(workflow: Workflow) -> None:
    """
    Ensure all `workflow.tabs[*].live_wf_modules` cache fresh render results.

    Raise UnneededExecution if the inputs become stale (at which point we don't
    care about results any more).

    WEBSOCKET NOTES: each wf_module is executed in turn. After each execution,
    we notify clients of its new columns and status.
    """
    tabs_work = await _load_tabs_wf_modules_and_input(workflow)

    for wf_modules, input_crr in tabs_work:
        # Execute one module at a time.
        #
        # We don't hold any lock throughout the loop: the loop can take a long
        # time; it might be run multiple times simultaneously (even on
        # different computers); and `await` doesn't work with locks.
        for wf_module in wf_modules:
            input_crr = await execute_wfmodule(workflow, wf_module, input_crr)
