import asyncio
import contextlib
import datetime
from typing import Any, Dict, Optional, Tuple
from channels.db import database_sync_to_async
from cjworkbench.types import ProcessResult, StepResultShape, TableShape
from server import notifications
from server.models import LoadedModule, Params, WfModule, Workflow
from server.notifications import OutputDelta
from server import websockets
from .types import UnneededExecution, TabCycleError, TabOutputUnreachableError
from . import renderprep


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
def _execute_wfmodule_pre(
    workflow: Workflow,
    wf_module: WfModule,
    params: Params,
    input_table_shape: TableShape,
    tab_shapes: Dict[str, Optional[StepResultShape]]
) -> Tuple:
    """
    First step of execute_wfmodule().

    Return a Tuple in this order:
        * loaded_module: a ModuleVersion for dispatching render
        * fetch_result: optional ProcessResult for dispatching render
        * param_values: a dict for dispatching render

    Raise TabCycleError or TabOutputUnreachableError if the module depends on
    tabs with errors. (We won't call the render() method in that case.)

    All this runs synchronously within a database lock. (It's a separate
    function so that when we're done awaiting it, we can continue executing in
    a context that doesn't use a database thread.)

    `tab_shapes.keys()` must be ordered as the Workflow's tabs are.
    """
    # raises UnneededExecution
    with locked_wf_module(workflow, wf_module) as safe_wf_module:
        module_version = safe_wf_module.module_version
        fetch_result = safe_wf_module.get_fetch_result()
        render_context = renderprep.RenderContext(
            workflow.id,
            input_table_shape,
            tab_shapes,
            params  # ugh
        )
        param_values = renderprep.get_param_values(params, render_context)
        loaded_module = LoadedModule.for_module_version_sync(module_version)

        return (loaded_module, fetch_result, param_values)


@database_sync_to_async
def _execute_wfmodule_save(workflow: Workflow, wf_module: WfModule,
                           result: ProcessResult) -> OutputDelta:
    """
    Call wf_module.cache_render_result() and build OutputDelta.

    All this runs synchronously within a database lock. (It's a separate
    function so that when we're done awaiting it, we can continue executing in
    a context that doesn't use a database thread.)

    Raise UnneededExecution if the WfModule has changed in the interim.
    """
    # raises UnneededExecution
    with locked_wf_module(workflow, wf_module) as safe_wf_module:
        if safe_wf_module.notifications:
            stale_crr = safe_wf_module.get_stale_cached_render_result()
            if stale_crr is None:
                stale_result = None
            else:
                # Read entire old Parquet file, blocking
                stale_result = stale_crr.result
        else:
            stale_result = None

        safe_wf_module.cache_render_result(
            safe_wf_module.last_relevant_delta_id,
            result
        )

        if safe_wf_module.notifications and result != stale_result:
            safe_wf_module.has_unseen_notification = True
            safe_wf_module.save(update_fields=['has_unseen_notification'])
            return notifications.OutputDelta(safe_wf_module,
                                             stale_result, result)
        else:
            return None  # nothing to email


async def _render_wfmodule(
    workflow: Workflow,
    wf_module: WfModule,
    params: Params,
    tab_name: str,
    input_result: Optional[ProcessResult],  # None for first module in tab
    tab_shapes: Dict[str, Optional[StepResultShape]]
) -> ProcessResult:
    """
    Prepare and call `wf_module`'s `render()`; return a ProcessResult.

    The actual render runs in a background thread so the event loop can process
    other events.
    """
    if wf_module.order > 0 and input_result.status != 'ok':
        return ProcessResult()  # 'unreachable'

    try:
        loaded_module, fetch_result, param_values = (
            await _execute_wfmodule_pre(workflow, wf_module, params,
                                        input_result.table_shape, tab_shapes)
        )
    except TabCycleError:
        return ProcessResult(error=(
            'The chosen tab depends on this one. Please choose another tab.'
        ))
    except TabOutputUnreachableError:
        return ProcessResult(error=(
            'The chosen tab has no output. '
            'Please change that tab or choose another.'
        ))

    # Render may take a while. run_in_executor to push that slowdown to a
    # thread and keep our event loop responsive.
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, loaded_module.render,
                                      input_result, param_values, tab_name,
                                      fetch_result)


async def execute_wfmodule(
    workflow: Workflow,
    wf_module: WfModule,
    params: Params,
    tab_name: str,
    input_result: ProcessResult,
    tab_shapes: Dict[str, Optional[StepResultShape]]
) -> ProcessResult:
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
    # delta_id won't change throughout this function
    delta_id = wf_module.last_relevant_delta_id

    # may raise UnneededExecution
    result = await _render_wfmodule(workflow, wf_module, params, tab_name,
                                    input_result, tab_shapes)

    # may raise UnneededExecution
    output_delta = await _execute_wfmodule_save(workflow, wf_module, result)

    await websockets.ws_client_send_delta_async(workflow.id, {
        'updateWfModules': {
            str(wf_module.id): build_status_dict(result, delta_id)
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
    return result


def build_status_dict(result: ProcessResult, delta_id: int) -> Dict[str, Any]:
    quick_fixes = [qf.to_dict() for qf in result.quick_fixes]
    output_columns = [{'name': c.name, 'type': c.type.value}
                      for c in result.columns]

    return {
        'quick_fixes': quick_fixes,
        'output_columns': output_columns,
        'output_error': result.error,
        'output_status': result.status,
        'output_n_rows': len(result.dataframe),
        'cached_render_result_delta_id': delta_id,
    }
