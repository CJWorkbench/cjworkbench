import asyncio
import contextlib
import datetime
from typing import Any, Dict, Tuple
from channels.db import database_sync_to_async
from server import notifications
from server.models import CachedRenderResult, LoadedModule, WfModule, Workflow
from server.modules.types import ProcessResult
from server import websockets
from .types import UnneededExecution


@contextlib.contextmanager
def locked_wf_module(workflow, wf_module):
    """
    Supplies concurrency guarantees for execute_wfmodule().

    Usage:

    with locked_wf_module(workflow, wf_module) as safe_wf_module:
        ...

    Raises UnneededExecution if the wf_module or workflow have changed.
    """
    try:
        with workflow.cooperative_lock():
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
def _execute_wfmodule_pre(workflow: Workflow, wf_module: WfModule,
                          input_crr: CachedRenderResult) -> Tuple:
    """
    First step of execute_wfmodule().

    Returns a Tuple in this order:
        * cached_render_result: if non-None, the quick return value of
          execute_wfmodule().
        * loaded_module: a ModuleVersion for dispatching render
        * input_result: Result from previous module
        * params: Params for dispatching render
        * fetch_result: optional ProcessResult for dispatching render

    All this runs synchronously within a database lock. (It's a separate
    function so that when we're done awaiting it, we can continue executing in
    a context that doesn't use a database thread.)
    """
    with locked_wf_module(workflow, wf_module) as safe_wf_module:
        cached_render_result = safe_wf_module.cached_render_result
        if cached_render_result is not None:
            # If the cache is good, skip everything.
            return (cached_render_result, None, None, None, None)

        module_version = safe_wf_module.module_version

        # Read the entire input Parquet file.
        #
        # Usually, this will return a fetched result from memory.
        # (input_crr.result is a cached value, and it's set during creation; so
        # if we created input_crr while executing the previous module, this
        # won't read from S3.)
        if input_crr is not None:
            input_result = input_crr.result
        else:
            input_result = ProcessResult()

        params = safe_wf_module.get_params()
        fetch_result = safe_wf_module.get_fetch_result()

        loaded_module = LoadedModule.for_module_version_sync(module_version)

        return (None, loaded_module, input_result, params, fetch_result)


@database_sync_to_async
def _execute_wfmodule_save(workflow: Workflow, wf_module: WfModule,
                           result: ProcessResult) -> Tuple:
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
    with locked_wf_module(workflow, wf_module) as safe_wf_module:
        if safe_wf_module.notifications:
            stale_crr = safe_wf_module.get_stale_cached_render_result()
            # Read entire old Parquet file, blocking
            old_result = stale_crr.result
        else:
            old_result = None

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


async def _render_wfmodule(workflow: Workflow, wf_module: WfModule,
                           input_crr: CachedRenderResult
                           ) -> Tuple[ProcessResult, ProcessResult,
                                      CachedRenderResult]:
    """
    Prepare and call `wf_module`'s `render()`.

    Return (None, cached_render_result) if the render is spurious.

    Return (result, None) otherwise.
    """
    if input_crr is not None and input_crr.status != 'ok':
        # The previous module is errored or unreachable. That means _this_
        # module is unreachable.
        result = ProcessResult()  # 'unreachable'
        return (result, None)
    else:
        (cached_render_result, loaded_module, input_result, params,
         fetch_result) = await _execute_wfmodule_pre(workflow, wf_module,
                                                     input_crr)

        # If the cached render result is valid, we're done!
        if cached_render_result is not None:
            return (None, cached_render_result)

        table = input_result.dataframe
        loop = asyncio.get_event_loop()
        # Render may take a while. run_in_executor to push that slowdown to a
        # thread and keep our event loop responsive.
        result = await loop.run_in_executor(None, loaded_module.render, table,
                                            params, fetch_result)
        return (result, None)


async def execute_wfmodule(workflow: Workflow, wf_module: WfModule,
                           input_crr: CachedRenderResult
                           ) -> CachedRenderResult:
    """
    Render a single WfModule; cache, broadcast and return output.

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
    # may raise UnneededExecution
    result, cached_render_result = await _render_wfmodule(workflow, wf_module,
                                                          input_crr)

    if cached_render_result is None:
        # may raise UnneededExecution
        cached_render_result, output_delta = \
            await _execute_wfmodule_save(workflow, wf_module, result)
    else:
        output_delta = None

    await websockets.ws_client_send_delta_async(workflow.id, {
        'updateWfModules': {
            str(wf_module.id): build_status_dict(cached_render_result)
        }
    })

    # Email notification if data has changed. Do this outside of the database
    # lock, because SMTP can be slow, and Django's email backend is
    # synchronous.
    if output_delta:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, notifications.email_output_delta,
                                   output_delta, datetime.datetime.now())

    # TODO if there's no change, is it possible for us to skip the render
    # of future modules, setting their cached_render_result_delta_id =
    # last_relevant_delta_id?  Investigate whether this is worthwhile.

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
