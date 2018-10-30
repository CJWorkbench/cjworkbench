import asyncio
import contextlib
import datetime
from typing import Any, Dict, Optional, Tuple
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from server import dispatch, notifications
from server.models import CachedRenderResult, WfModule, Workflow
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

    Raises UnneededExecution.
    """
    with wf_module.workflow.cooperative_lock():
        # safe_wf_module: locked at the database level.
        delta_id = wf_module.last_relevant_delta_id
        try:
            safe_wf_module = WfModule.objects \
                .filter(workflow_id=wf_module.workflow_id) \
                .filter(last_relevant_delta_id=delta_id) \
                .get(pk=wf_module.pk)
        except WfModule.DoesNotExist:
            # Module was deleted or changed input/params _after_ we requested
            # render but _before_ we start rendering
            raise UnneededExecution

        retval = yield safe_wf_module

    return retval


@database_sync_to_async
def mark_wfmodule_unreachable(wf_module: WfModule):
    """
    Writes that a WfModule is unreachable.

    CONCURRENCY NOTES: same as in execute_wfmodule().
    """
    with locked_wf_module(wf_module) as safe_wf_module:
        unreachable = ProcessResult()
        cached_render_result = safe_wf_module.cache_render_result(
            safe_wf_module.last_relevant_delta_id,
            unreachable
        )

        # Save safe_wf_module, not wf_module, because we know we've only
        # changed the cached_render_result columns. (We know because we
        # locked the row before fetching it.) `wf_module.save()` might
        # overwrite some newer values.
        safe_wf_module.save()

        return cached_render_result


@database_sync_to_async
def _execute_wfmodule_pre(wf_module: WfModule) -> Tuple:
    """
    First step of execute_wfmodule().

    Returns a Tuple in this order:
        * cached_render_result: if non-None, the quick return value of
          execute_wfmodule().
        * wf_module: an up-to-date version of the input.
        * module_version: a ModuleVersion for dispatching render
        * params: Params for dispatching render
        * fetch_result: optional ProcessResult for dispatching render
        * old_result: if wf_module.notifications is set, the previous
          result we'll compare against after render.

    All this runs synchronously within a database lock. (It's a separate
    function so that when we're done awaiting it, we can continue executing in
    a context that doesn't use a database thread.)
    """
    with locked_wf_module(wf_module) as safe_wf_module:
        cached_render_result = wf_module.get_cached_render_result()

        old_result = None
        if cached_render_result:
            # If the cache is good, skip everything. No need for old_result,
            # because we know the output won't change (since we won't even run
            # render()).
            if (cached_render_result.delta_id
                    == wf_module.last_relevant_delta_id):
                return (cached_render_result, None, None, None, None, None)

            if safe_wf_module.notifications:
                old_result = cached_render_result.result

        module_version = wf_module.module_version
        params = safe_wf_module.get_params()
        fetch_result = safe_wf_module.get_fetch_result()

        return (None, safe_wf_module, module_version, params, fetch_result,
                old_result)


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
            output_delta = notifications.OutputDelta(safe_wf_module,
                                                     old_result, result)
        else:
            output_delta = None

        # Save safe_wf_module, not wf_module, because we know we've only
        # changed the cached_render_result columns. (We know because we
        # locked the row before fetching it.) `wf_module.save()` might
        # overwrite some newer values.
        safe_wf_module.save()

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
    (cached_render_result, wf_module, module_version, params, fetch_result,
     old_result) = await _execute_wfmodule_pre(wf_module)

    # If the cached render result is valid, we're done!
    if cached_render_result is not None:
        return cached_render_result

    table = last_result.dataframe
    loop = asyncio.get_event_loop()
    # Render may take a while. run_in_executor to push that slowdown to a
    # thread and keep our event loop responsive.
    result = await loop.run_in_executor(None, dispatch.module_dispatch_render,
                                        module_version, params, table,
                                        fetch_result)

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

    output_columns = [{'name': c.name, 'type': c.type}
                      for c in cached_result.columns]

    return {
        'error_msg': cached_result.error,
        'status': cached_result.status,
        'quick_fixes': quick_fixes,
        'output_columns': output_columns,
        'output_n_rows': len(cached_result),
        'last_relevant_delta_id': cached_result.delta_id,
        'cached_render_result_delta_id': cached_result.delta_id,
    }


@database_sync_to_async
def _load_wf_modules_and_input(workflow: Workflow):
    """
    Finds (stale_wf_modules, previous_cached_result_or_none) from the database.

    If all modules are up-to-date, returns ([], output_cached_result). Yes,
    beware: if we aren't rendering, we return *output*, and if we are rendering
    we return *input*. This is convenient for the caller.

    If there's a race, the returned `stale_wf_modules` may be too short, and
    `input_table` may be wrong. That should be fine because `execute_wfmodule`
    will raise an exception before starting work.
    """
    with workflow.cooperative_lock():
        # 1. Load list of wf_modules
        wf_modules = list(workflow.wf_modules.all())

        if not wf_modules:
            return [], None

        # 2. Find index of first one that needs render
        index = 0
        while index < len(wf_modules) and not _needs_render(wf_modules[index]):
            index += 1

        wf_modules_needing_render = wf_modules[index:]

        if not wf_modules_needing_render:
            # We're up to date!
            output = None

            return [], output

        # 4. Load input
        if index == 0:
            prev_result = None
        else:
            # if the CachedRenderResult is obsolete because of a race (it's on
            # the filesystem as well as in the DB), we'll get _something_ back:
            # this method doesn't raise exceptions. There's no harm done if the
            # value is wrong: we'll check that later anyway.
            prev_result = wf_modules[index - 1].get_cached_render_result()

        return wf_modules_needing_render, prev_result


async def execute_workflow(workflow: Workflow) -> Optional[CachedRenderResult]:
    """
    Ensure all `workflow.wf_modules` have valid cached render results.

    Raise UnneededExecution if the inputs become stale (at which point we don't
    care about results any more).

    WEBSOCKET NOTES: each wf_module is executed in turn. After each execution,
    we notify clients of its new columns and status.
    """

    wf_modules, last_cached_result = await _load_wf_modules_and_input(
        workflow
    )

    if not wf_modules:
        return last_cached_result

    # Execute one module at a time.
    #
    # We don't hold any lock throughout the loop: the loop can take a long
    # time; it might be run multiple times simultaneously (even on different
    # computers); and `await` doesn't work with locks.
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

            last_cached_result = await execute_wfmodule(wf_module, last_result)

        await websockets.ws_client_send_delta_async(workflow.id, {
            'updateWfModules': {
                str(wf_module.id): build_status_dict(last_cached_result)
            }
        })


async def execute_ignoring_error(workflow: Workflow
                                 ) -> Optional[CachedRenderResult]:
    """
    `execute_workflow(workflow)` and stop on `UnneededExecution`.

    Stops when it catches UnneededExecution or when workflow is up-to-date.

    Does not return anything, and should never raise any exception. To fire
    and forget call `asyncio.ensure_future(execute_ignoring_error(workflow))`.

    TODO render in a worker process; nix this terrible, terrible design. This
    design keeps tons of DataFrames in memory simultaneously.
    """
    try:
        return await execute_workflow(workflow)
    except UnneededExecution:
        pass
