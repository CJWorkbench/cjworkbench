import asyncio
import contextlib
import datetime
from pathlib import Path
import tempfile
from typing import Any, Dict, Optional, Tuple
from cjworkbench.sync import database_sync_to_async
from cjwkernel.types import (
    ArrowTable,
    FetchResult,
    I18nMessage,
    RenderError,
    RenderResult,
    Tab,
)
from cjwstate import minio, rendercache
from cjwstate.models import StoredObject, WfModule, Workflow
from cjwstate.models.loaded_module import LoadedModule
from server import websockets
from renderer import notifications
from .types import (
    TabCycleError,
    TabOutputUnreachableError,
    UnneededExecution,
    PromptingError,
)
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
                    pk=wf_module.pk, is_deleted=False, last_relevant_delta_id=delta_id
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


def _load_fetch_result(wf_module: WfModule, path: Path) -> Optional[FetchResult]:
    """
    Download user-selected StoredObject to `path`, so render() can read it.

    Edge cases:

    * Leave `path` alone if the user did not select a StoredObject.
    * Return None if there is no user-selected StoredObject.
    * Leave `path` alone if the user-seleted StoredObject is an error.
    
    The caller should ensure "leave `path` alone" means "return an empty
    FetchResult". The FetchResult may still have an error.
    """
    try:
        stored_object = wf_module.stored_objects.get(
            stored_at=wf_module.stored_data_version
        )
        minio.download(stored_object.bucket, stored_object.key, path)
    except StoredObject.DoesNotExist:
        pass  # leave the file with 0 bytes
    except FileNotFoundError:
        # A few StoredObjects -- very old ones with size=0 -- are
        # *intentionally* not in minio.
        pass  # leave the file with 0 bytes

    if wf_module.fetch_error:
        errors = [RenderError(I18nMessage.TODO_i18n(wf_module.fetch_error))]
    else:
        errors = []
    return FetchResult(path, errors)


@database_sync_to_async
def _execute_wfmodule_pre(
    workflow: Workflow,
    wf_module: WfModule,
    raw_params: Dict[str, Any],
    input_table: ArrowTable,
    tab_results: Dict[Tab, Optional[RenderResult]],
    fetch_result_path: Path,
) -> Tuple[Optional[LoadedModule], Optional[RenderResult], Dict[str, Any]]:
    """
    First step of execute_wfmodule().

    Return a Tuple in this order:
        * loaded_module: a ModuleVersion for dispatching render
        * fetch_result: optional FetchResult for dispatching render
        * params: a Params for dispatching render

    Raise TabCycleError or TabOutputUnreachableError if the module depends on
    tabs with errors. (We won't call the render() method in that case.)

    Raise PromptingError if the module parameters are invalid. (We'll skip
    render() and prompt the user with quickfixes in that case.)

    All this runs synchronously within a database lock. (It's a separate
    function so that when we're done awaiting it, we can continue executing in
    a context that doesn't use a database thread.)

    `tab_results.keys()` must be ordered as the Workflow's tabs are.
    """
    # raises UnneededExecution
    with locked_wf_module(workflow, wf_module) as safe_wf_module:
        module_version = safe_wf_module.module_version
        loaded_module = LoadedModule.for_module_version_sync(module_version)
        if loaded_module is None:
            # module was deleted. Skip other fetches.
            return (None, None, {})

        fetch_result = _load_fetch_result(safe_wf_module, fetch_result_path)
        render_context = renderprep.RenderContext(
            workflow.id, wf_module.id, input_table, tab_results, raw_params  # ugh
        )
        params = renderprep.get_param_values(
            module_version.param_schema, raw_params, render_context
        )

        return (loaded_module, fetch_result, params)


@database_sync_to_async
def _execute_wfmodule_save(
    workflow: Workflow, wf_module: WfModule, result: RenderResult
) -> notifications.OutputDelta:
    """
    Call rendercache.cache_render_result() and build notifications.OutputDelta.

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
                with rendercache.open_cached_render_result(stale_crr) as stale_result:
                    pass  # stale_result is deleted from disk but still mmapped
        else:
            stale_result = None

        rendercache.cache_render_result(
            workflow, safe_wf_module, wf_module.last_relevant_delta_id, result
        )

        if safe_wf_module.notifications and result != stale_result:
            safe_wf_module.has_unseen_notification = True
            safe_wf_module.save(update_fields=["has_unseen_notification"])
            return notifications.OutputDelta(
                safe_wf_module.workflow.owner,
                safe_wf_module.workflow,
                safe_wf_module,
                stale_result,
                result,
            )
        else:
            return None  # nothing to email


async def _render_wfmodule(
    workflow: Workflow,
    wf_module: WfModule,
    raw_params: Dict[str, Any],
    tab: Tab,
    input_result: RenderResult,
    tab_results: Dict[Tab, Optional[RenderResult]],
    output_path: Path,
) -> RenderResult:
    """
    Prepare and call `wf_module`'s `render()`; return a ProcessResult.

    The actual render runs in a background thread so the event loop can process
    other events.
    """
    if wf_module.order > 0 and input_result.status != "ok":
        return RenderResult()  # 'unreachable'

    with tempfile.NamedTemporaryFile() as fetch_result_file:
        fetch_result_path = Path(fetch_result_file.name)

        try:
            loaded_module, fetch_result, params = await _execute_wfmodule_pre(
                workflow,
                wf_module,
                raw_params,
                input_result.table,
                tab_results,
                fetch_result_path,
            )
        except TabCycleError:
            return RenderResult.from_deprecated_error(
                "The chosen tab depends on this one. Please choose another tab."
            )
        except TabOutputUnreachableError:
            return RenderResult.from_deprecated_error(
                "The chosen tab has no output. Please select another one."
            )
        except PromptingError as err:
            return RenderResult.from_deprecated_error(
                err.as_error_str(), quick_fixes=err.as_quick_fixes()
            )

        if loaded_module is None:
            return RenderResult.from_deprecated_error(
                "Please delete this step: an administrator uninstalled its code."
            )

        # Render may take a while. run_in_executor to push that slowdown to a
        # thread and keep our event loop responsive.
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            loaded_module.render,
            input_result.table,
            params,
            tab,
            fetch_result,
            output_path,
        )


async def execute_wfmodule(
    workflow: Workflow,
    wf_module: WfModule,
    params: Dict[str, Any],
    tab: Tab,
    input_result: RenderResult,
    tab_results: Dict[Tab, Optional[RenderResult]],
    output_path: Path,
) -> RenderResult:
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
    result = await _render_wfmodule(
        workflow, wf_module, params, tab, input_result, tab_results, output_path
    )

    # may raise UnneededExecution
    output_delta = await _execute_wfmodule_save(workflow, wf_module, result)

    await websockets.ws_client_send_delta_async(
        workflow.id,
        {"updateWfModules": {str(wf_module.id): build_status_dict(result, delta_id)}},
    )

    # Email notification if data has changed. Do this outside of the database
    # lock, because SMTP can be slow, and Django's email backend is
    # synchronous.
    if output_delta:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            notifications.email_output_delta,
            output_delta,
            datetime.datetime.now(),
        )

    # TODO if there's no change, is it possible for us to skip the render
    # of future modules, setting their cached_render_result_delta_id =
    # last_relevant_delta_id?  Investigate whether this is worthwhile.
    return result


def build_status_dict(result: RenderResult, delta_id: int) -> Dict[str, Any]:
    if result.errors:
        if result.errors[0].message.id != "TODO_i18n":
            raise RuntimeError("TODO serialize i18n-ready messages")
        error = result.errors[0].message.args["text"]
        quick_fixes = [qf.to_dict() for qf in result.errors[0].quick_fixes]
    else:
        error = ""
        quick_fixes = []

    return {
        "quick_fixes": quick_fixes,
        "output_columns": [c.to_dict() for c in result.table.metadata.columns],
        "output_error": error,
        "output_status": result.status,
        "output_n_rows": result.table.metadata.n_rows,
        "cached_render_result_delta_id": delta_id,
    }
