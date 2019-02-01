import asyncio
import contextlib
import datetime
from typing import Any, Dict, Tuple
from channels.db import database_sync_to_async
from server import notifications
from server.models import CachedRenderResult, LoadedModule, WfModule, Workflow
from server.modules.types import ProcessResult
from server import websockets


def _needs_render(wf_module: WfModule) -> bool:
    return (
        wf_module.last_relevant_delta_id
        != wf_module.cached_render_result_delta_id
    )


class UnneededExecution(Exception):
    """Indicates that a render would produce useless results."""
    pass


@contextlib.contextmanager
def locked_wf_module(wf_module):
    """
    Supplies concurrency guarantees for execute_wfmodule().

    Usage:

    with locked_wf_module(wf_module) as safe_wf_module:
        ...

    Raises UnneededExecution if the wf_module or workflow have changed.
    """
    try:
        with wf_module.workflow.cooperative_lock():
            # safe_wf_module: locked at the database level.
            delta_id = wf_module.last_relevant_delta_id
            try:
                safe_wf_module = WfModule.objects.get(
                    pk=wf_module.pk,
                    is_deleted=False,
                    last_relevant_delta_id=delta_id
                )
            except WfModule.DoesNotExist:
                # Module was deleted or changed input/params _after_ we
                # requested render but _before_ we start rendering
                raise UnneededExecution

            retval = yield safe_wf_module
    except Workflow.DoesNotExist:
        # Workflow was deleted after execute began
        raise UnneededExecution

    return retval


@database_sync_to_async
def mark_wfmodule_unreachable(wf_module: WfModule):
    """
    Writes that a WfModule is unreachable.

    CONCURRENCY NOTES: same as in execute_wfmodule().
    """
    with locked_wf_module(wf_module) as safe_wf_module:
        unreachable = ProcessResult()
        return safe_wf_module.cache_render_result(
            safe_wf_module.last_relevant_delta_id,
            unreachable
        )


@database_sync_to_async
def _execute_wfmodule_pre(wf_module: WfModule) -> Tuple:
    """
    First step of execute_wfmodule().

    Returns a Tuple in this order:
        * cached_render_result: if non-None, the quick return value of
          execute_wfmodule().
        * loaded_module: a ModuleVersion for dispatching render
        * params: Params for dispatching render
        * fetch_result: optional ProcessResult for dispatching render
        * old_result: if wf_module.notifications is set, the previous
          result we'll compare against after render.

    All this runs synchronously within a database lock. (It's a separate
    function so that when we're done awaiting it, we can continue executing in
    a context that doesn't use a database thread.)
    """
    with locked_wf_module(wf_module) as safe_wf_module:
        cached_render_result = wf_module.cached_render_result
        if cached_render_result is not None:
            # If the cache is good, skip everything. No need for old_result,
            # because we know the output won't change (since we won't even run
            # render()).
            return (cached_render_result, None, None, None, None)

        # Get a handle on `old_result`, if we're about to re-render and we want
        # to notify the user if new_result != old_result
        old_result = None
        if safe_wf_module.notifications:
            stale_result = wf_module.get_stale_cached_render_result()
            if stale_result is not None:
                old_result = stale_result.result

        module_version = wf_module.module_version
        params = safe_wf_module.get_params()
        fetch_result = safe_wf_module.get_fetch_result()

        loaded_module = LoadedModule.for_module_version_sync(module_version)

        return (None, loaded_module, params, fetch_result, old_result)


@database_sync_to_async
def _execute_wfmodule_save(wf_module: WfModule, result: ProcessResult,
                           old_result: ProcessResult) -> Tuple:
    """
    Second database step of execute_wfmodule().

    Writes result (and maybe has_unseen_notification) to the WfModule in the
    database and returns a Tuple in this order:
        * cached_render_result: the return value of execute_wfmodule().
        * output_delta: if non-None, an OutputDelta to email to the Workflow
          owner.

    All this runs synchronously within a database lock. (It's a separate
    function so that when we're done awaiting it, we can continue executing in
    a context that doesn't use a database thread.)

    Raises UnneededExecution if the WfModule has changed in the interim.
    """
    with locked_wf_module(wf_module) as safe_wf_module:
        if (safe_wf_module.last_relevant_delta_id
                != wf_module.last_relevant_delta_id):
            raise UnneededExecution

        cached_render_result = safe_wf_module.cache_render_result(
            safe_wf_module.last_relevant_delta_id,
            result
        )

        if safe_wf_module.notifications and result != old_result:
            safe_wf_module.has_unseen_notification = True
            safe_wf_module.save(update_fields=['has_unseen_notification'])
            output_delta = notifications.OutputDelta(safe_wf_module,
                                                     old_result, result)
        else:
            output_delta = None

        return (cached_render_result, output_delta)


async def execute_wfmodule(wf_module: WfModule,
                           last_result: ProcessResult) -> CachedRenderResult:
    """
    Render a single WfModule; cache and return output.

    CONCURRENCY NOTES: This function is reasonably concurrency-friendly:

    * It returns a valid cache result immediately.
    * It checks with the database that `wf_module` hasn't been deleted from
      its workflow.
    * It checks with the database that `wf_module` hasn't been deleted from
      the database entirely.
    * It checks with the database that `wf_module` hasn't been modified. (It
      is very common for a user to request a module's output -- kicking off a
      sequence of `execute_wfmodule` -- and then change a param in a prior
      module, making all those calls obsolete.
    * It locks the workflow while collecting `render()` input data.
    * When writing results to the database, it avoids writing if the module has
      changed.

    These guarantees mean:

    * TODO It's relatively cheap to render twice.
    * Users who modify a WfModule while it's rendering will be stalled -- for
      as short a duration as possible.
    * When a user changes a workflow significantly, all prior renders will end
      relatively cheaply.

    Raises `UnneededExecution` when the input WfModule should not be rendered.
    """
    (cached_render_result, loaded_module, params, fetch_result, old_result
     ) = await _execute_wfmodule_pre(wf_module)

    # If the cached render result is valid, we're done!
    if cached_render_result is not None:
        return cached_render_result

    table = last_result.dataframe
    loop = asyncio.get_event_loop()
    # Render may take a while. run_in_executor to push that slowdown to a
    # thread and keep our event loop responsive.
    result = await loop.run_in_executor(None, loaded_module.render, table,
                                        params, fetch_result)

    cached_render_result, output_delta = \
        await _execute_wfmodule_save(wf_module, result, old_result)

    # Email notification if data has changed. Do this outside of the database
    # lock, because SMTP can be slow, and Django's email backend is
    # synchronous.
    if output_delta:
        notifications.email_output_delta(output_delta, datetime.datetime.now())

    # TODO if there's no change, is it possible for us to skip the render
    # and simply set cached_render_result_delta_id=last_relevant_delta_id?
    # Investigate whether this is a worthwhile optimization.

    return cached_render_result


def build_status_dict(cached_result: CachedRenderResult) -> Dict[str, Any]:
    quick_fixes = [qf.to_dict()
                   for qf in cached_result.quick_fixes]

    output_columns = [{'name': c.name, 'type': c.type.value}
                      for c in cached_result.columns]

    return {
        'quick_fixes': quick_fixes,
        'output_columns': output_columns,
        'output_error': cached_result.error,
        'output_status': cached_result.status,
        'output_n_rows': len(cached_result),
        'last_relevant_delta_id': cached_result.delta_id,
        'cached_render_result_delta_id': cached_result.delta_id,
    }


@database_sync_to_async
def _load_tabs_wf_modules_and_input(workflow: Workflow):
    """
    Queries for each tab's (stale_steps, previous_cached_result_or_none).

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

    for wf_modules, last_cached_result in tabs_work:
        # Execute one module at a time.
        #
        # We don't hold any lock throughout the loop: the loop can take a long
        # time; it might be run multiple times simultaneously (even on
        # different computers); and `await` doesn't work with locks.
        for wf_module in wf_modules:
            # The first module in the Workflow has last_cached_result=None.
            # Other than that, there's no recovering from any non='ok' result:
            # all subsequent results should be 'unreachable'
            if last_cached_result and last_cached_result.status != 'ok':
                last_cached_result = await mark_wfmodule_unreachable(wf_module)
            else:
                if last_cached_result:
                    last_result = last_cached_result.result
                else:
                    # First module has empty-DataFrame input.
                    last_result = ProcessResult()

                last_cached_result = await execute_wfmodule(wf_module,
                                                            last_result)

            await websockets.ws_client_send_delta_async(workflow.id, {
                'updateWfModules': {
                    str(wf_module.id): build_status_dict(last_cached_result)
                }
            })
