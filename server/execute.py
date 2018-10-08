import contextlib
from typing import Any, Dict, Optional
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from django.db import transaction
from pandas import DataFrame
from server import dispatch
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
def execute_wfmodule(wf_module: WfModule,
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
    with locked_wf_module(wf_module) as safe_wf_module:
        cached_render_result = wf_module.get_cached_render_result()

        # If the cache is good, just return it -- skipping the render() call
        if (
            cached_render_result
            and (cached_render_result.delta_id
                 == wf_module.last_relevant_delta_id)
        ):
            return cached_render_result

        module_version = wf_module.module_version
        params = safe_wf_module.get_params()
        fetch_result = safe_wf_module.get_fetch_result()

    # Release lock, so user gets a responsive experience from other threads
    table = last_result.dataframe
    result = dispatch.module_dispatch_render(module_version, params,
                                             table, fetch_result)

    with locked_wf_module(safe_wf_module) as safe_wf_module_2:
        if (safe_wf_module_2.last_relevant_delta_id
            != safe_wf_module.last_relevant_delta_id):
            raise UnneededExecution

        cached_render_result = safe_wf_module_2.cache_render_result(
            safe_wf_module_2.last_relevant_delta_id,
            result
        )

        # Save safe_wf_module_2, not wf_module, because we know we've only
        # changed the cached_render_result columns. (We know because we
        # locked the row before fetching it.) `wf_module.save()` might
        # overwrite some newer values.
        safe_wf_module_2.save()

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
        'last_relevant_delta_id': cached_result.delta_id,
    }



@database_sync_to_async
def _load_wf_modules_and_input(workflow: Workflow,
                               until_wf_module: Optional[WfModule]):
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

        # 3. Find index of last module we're requesting
        if until_wf_module:
            try:
                until_index = [m.id for m in wf_modules] \
                    .index(until_wf_module.id)
            except ValueError:
                # Module isn't in workflow any more
                raise UnneededExecution
        else:
            until_index = len(wf_modules) - 1

        wf_modules_needing_render = wf_modules[index:until_index + 1]

        if not wf_modules_needing_render:
            # We're up to date!
            if until_wf_module:
                # _needs_render() returned false, so we know we can fetch the
                # cached result. Load from `wf_modules`, not `until_wf_module`,
                # because the latter may be stale.
                output = wf_modules[until_index].get_cached_render_result()
            else:
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


async def execute_workflow(workflow: Workflow,
                           until_wf_module: Optional[WfModule]=None
                          ) -> Optional[CachedRenderResult]:
    """
    Ensures all `workflow.wf_modules` have valid cached render results.

    If `until_wf_module` is specified, stops execution early and returns the
    CachedRenderResult.

    raises UnneededExecution if the inputs become stale (at which point we
    don't care about the results any more).

    WEBSOCKET NOTES: each wf_module is executed in turn. After each execution,
    we notify clients of its new columns and status.
    """

    wf_modules, last_cached_result = await _load_wf_modules_and_input(
        workflow,
        until_wf_module
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

    if until_wf_module:
        return last_cached_result


def execute_and_wait(workflow: Workflow,
                     until_wf_module: Optional[WfModule]=None
                    ) -> Optional[CachedRenderResult]:
    try:
        return async_to_sync(execute_workflow)(workflow, until_wf_module)
    except UnneededExecution:
        # This error means, "whatever we're returning is invalid.
        #
        # But let's return something anyway, for now.
        #
        # TODO make clients handle the exception. It's relevant to them.
        if until_wf_module:
            return until_wf_module.get_cached_render_result()


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
