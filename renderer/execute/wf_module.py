import asyncio
from collections import namedtuple
import contextlib
import datetime
from functools import partial
import logging
from pathlib import Path
import time
from typing import Any, Dict, NamedTuple, Optional
from cjworkbench.sync import database_sync_to_async
from cjwkernel.chroot import ChrootContext
from cjwkernel.errors import ModuleError, format_for_user_debugging
from cjwkernel.types import (
    ArrowTable,
    FetchResult,
    I18nMessage,
    Params,
    RenderError,
    RenderResult,
    Tab,
)
from cjwkernel.util import tempfile_context
from cjwstate import clientside, minio, rabbitmq, rendercache
from cjwstate.models import StoredObject, WfModule, Workflow
import cjwstate.modules
from cjwstate.modules.types import ModuleZipfile
from renderer import notifications
from .types import (
    TabCycleError,
    TabOutputUnreachableError,
    UnneededExecution,
    PromptingError,
)
from . import renderprep


logger = logging.getLogger(__name__)


SaveResult = namedtuple("SaveResult", ["cached_render_result", "maybe_delta"])


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


def _load_fetch_result(
    wf_module: WfModule, basedir: Path, exit_stack: contextlib.ExitStack
) -> Optional[FetchResult]:
    """
    Download user-selected StoredObject to `basedir`, so render() can read it.

    Edge cases:

    Create no file (and return `None`) if the user did not select a
    StoredObject, or if the selected StoredObject does not point to a file
    on minio.

    The caller should ensure "leave `path` alone" means "return an empty
    FetchResult". The FetchResult may still have an error.
    """
    try:
        stored_object = wf_module.stored_objects.get(
            stored_at=wf_module.stored_data_version
        )
    except StoredObject.DoesNotExist:
        return None
    if not stored_object.key:
        return None

    with contextlib.ExitStack() as inner_stack:
        path = inner_stack.enter_context(
            tempfile_context(prefix="fetch-result-", dir=basedir)
        )

        try:
            minio.download(minio.StoredObjectsBucket, stored_object.key, path)
            # Download succeeded, so we no longer want to delete `path`
            # right _now_ ("now" means, "in inner_stack.close()"). Instead,
            # transfer ownership of `path` to exit_stack.
            exit_stack.callback(inner_stack.pop_all().close)
        except FileNotFoundError:
            # A few StoredObjects -- very old ones with size=0 -- are
            # *intentionally* not in minio. It turns out modules from that era
            # treated empty-file and None as identical. The _modules_ must
            # preserve that logic for backwards compatibility; so it's safe to
            # return `None` here.
            #
            # Other than that, if the file doesn't exist it's a race: either
            # the fetch result is too _new_ (it's in the database but its file
            # hasn't been written yet) or the fetch result is half-deleted (its
            # file was deleted and it's still in the database). In either case,
            # pretend the fetch result does not exist in the database -- i.e.,
            # return `None`.
            return None

    if wf_module.fetch_error:
        errors = [RenderError(I18nMessage.TODO_i18n(wf_module.fetch_error))]
    elif wf_module.fetch_errors:
        # TODO_i18n make this the only case
        errors = wf_module.fetch_errors
    else:
        errors = []
    return FetchResult(path, errors)


def _wrap_render_errors(render_call):
    try:
        return render_call()
    except ModuleError as err:
        return RenderResult(
            errors=[
                RenderError(
                    I18nMessage.trans(
                        "py.renderer.execute.wf_module.user_visible_bug_during_render",
                        default="Something unexpected happened. We have been notified and are "
                        "working to fix it. If this persists, contact us. Error code: {message}",
                        args={"message": format_for_user_debugging(err)},
                    )
                )
            ]
        )


def invoke_render(
    module_zipfile: ModuleZipfile,
    *,
    chroot_context: ChrootContext,
    basedir: Path,
    input_table: ArrowTable,
    params: Params,
    tab: Tab,
    fetch_result: Optional[FetchResult],
    output_filename: str,
) -> RenderResult:
    """
    Use kernel to process `table` with module `render` function.

    Raise `ModuleError` on error. (This is usually the module author's fault.)

    Log any ModuleError. Also log success.

    This synchronous method can be slow for complex modules or large
    datasets. Consider calling it from an executor.
    """
    time1 = time.time()
    begin_status_format = "%s:render() (%d rows, %d cols, %0.1fMB)"
    begin_status_args = (
        module_zipfile.path.name,
        input_table.metadata.n_rows,
        len(input_table.metadata.columns),
        input_table.n_bytes_on_disk / 1024 / 1024,
    )
    logger.info(begin_status_format + " begin", *begin_status_args)
    status = "???"
    try:
        result = cjwstate.modules.kernel.render(
            module_zipfile.compile_code_without_executing(),
            chroot_context=chroot_context,
            basedir=basedir,
            input_table=input_table,
            params=params,
            tab=tab,
            fetch_result=fetch_result,
            output_filename=output_filename,
        )
        status = "(%drows, %dcols, %0.1fMB)" % (
            result.table.metadata.n_rows,
            len(result.table.metadata.columns),
            result.table.n_bytes_on_disk / 1024 / 1024,
        )
        return result
    except ModuleError as err:
        logger.exception("Exception in %s:render", module_zipfile.path.name)
        status = type(err).__name__
        raise
    finally:
        time2 = time.time()

        logger.info(
            begin_status_format + " => %s in %dms",
            *begin_status_args,
            status,
            int((time2 - time1) * 1000),
        )


class ExecuteStepPreResult(NamedTuple):
    fetch_result: Optional[FetchResult]
    params: Dict[str, Any]


@database_sync_to_async
def _execute_wfmodule_pre(
    basedir: Path,
    exit_stack: contextlib.ExitStack,
    workflow: Workflow,
    wf_module: WfModule,
    module_zipfile: ModuleZipfile,
    raw_params: Dict[str, Any],
    input_table: ArrowTable,
    tab_results: Dict[Tab, Optional[RenderResult]],
) -> ExecuteStepPreResult:
    """
    First step of execute_wfmodule().

    Raise TabCycleError or TabOutputUnreachableError if the module depends on
    tabs with errors. (We won't call the render() method in that case.)

    Raise PromptingError if the module parameters are invalid. (We'll skip
    render() and prompt the user with quickfixes in that case.)

    Raise UnneededExecution if `wf_module` has changed.

    All this runs synchronously within a database lock. (It's a separate
    function so that when we're done awaiting it, we can continue executing in
    a context that doesn't use a database thread.)

    `tab_results.keys()` must be ordered as the Workflow's tabs are.
    """
    # raises UnneededExecution
    with locked_wf_module(workflow, wf_module) as safe_wf_module:
        fetch_result = _load_fetch_result(safe_wf_module, basedir, exit_stack)

        module_spec = module_zipfile.get_spec()
        param_schema = module_spec.get_param_schema()
        render_context = renderprep.RenderContext(
            wf_module.id,
            input_table,
            tab_results,
            basedir,
            exit_stack,
            raw_params,  # ugh
        )
        # raise TabCycleError, TabOutputUnreachableError, PromptingError
        params = renderprep.get_param_values(param_schema, raw_params, render_context)

        return ExecuteStepPreResult(fetch_result, params)


@database_sync_to_async
def _execute_wfmodule_save(
    workflow: Workflow, wf_module: WfModule, result: RenderResult
) -> SaveResult:
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
                try:
                    # Read entire old Parquet file, blocking
                    with rendercache.open_cached_render_result(
                        stale_crr
                    ) as stale_result:
                        pass  # stale_result is deleted from disk but still mmapped
                except rendercache.CorruptCacheError:
                    # No, let's not send an email. Corrupt cache probably means
                    # we've been messing with our codebase.
                    logger.exception(
                        "Ignoring CorruptCacheError on workflow %d, wf_module %d because we are about to overwrite it",
                        workflow.id,
                        wf_module.id,
                    )
                    stale_result = None
        else:
            stale_result = None

        rendercache.cache_render_result(
            workflow, safe_wf_module, wf_module.last_relevant_delta_id, result
        )

        if (
            safe_wf_module.notifications
            and stale_result is not None
            and result != stale_result
        ):
            safe_wf_module.has_unseen_notification = True
            safe_wf_module.save(update_fields=["has_unseen_notification"])
            maybe_delta = notifications.OutputDelta(
                safe_wf_module.workflow.owner,
                safe_wf_module.workflow,
                safe_wf_module,
                stale_result,
                result,
            )
        else:
            maybe_delta = None  # nothing to email
        return SaveResult(safe_wf_module.cached_render_result, maybe_delta)


async def _render_wfmodule(
    chroot_context: ChrootContext,
    workflow: Workflow,
    wf_module: WfModule,
    module_zipfile: Optional[ModuleZipfile],
    raw_params: Dict[str, Any],
    tab: Tab,
    input_result: RenderResult,
    tab_results: Dict[Tab, Optional[RenderResult]],
    output_path: Path,
) -> RenderResult:
    """
    Prepare and call `wf_module`'s `render()`; return a RenderResult.

    The actual render runs in a background thread so the event loop can process
    other events.
    """
    basedir = output_path.parent

    if wf_module.order > 0 and input_result.status != "ok":
        return RenderResult()  # 'unreachable'

    if module_zipfile is None:
        return RenderResult(
            errors=[
                RenderError(
                    I18nMessage.trans(
                        "py.renderer.execute.wf_module.noModule",
                        default="Please delete this step: an administrator uninstalled its code.",
                    )
                )
            ]
        )

    # exit_stack: stuff that gets deleted when the render is done
    with contextlib.ExitStack() as exit_stack:
        try:
            # raise UnneededExecution, TabCycleError, TabOutputUnreachableError,
            # PromptingError
            fetch_result, params = await _execute_wfmodule_pre(
                basedir,
                exit_stack,
                workflow,
                wf_module,
                module_zipfile,
                raw_params,
                input_result.table,
                tab_results,
            )
        except TabCycleError:
            return RenderResult(
                errors=[
                    RenderError(
                        I18nMessage.trans(
                            "py.renderer.execute.wf_module.TabCycleError",
                            default="The chosen tab depends on this one. Please choose another tab.",
                        )
                    )
                ]
            )
        except TabOutputUnreachableError:
            return RenderResult(
                errors=[
                    RenderError(
                        I18nMessage.trans(
                            "py.renderer.execute.wf_module.TabOutputUnreachableError",
                            default="The chosen tab has no output. Please select another one.",
                        )
                    )
                ]
            )
        except PromptingError as err:
            return RenderResult(errors=err.as_render_errors())

        # Render may take a while. run_in_executor to push that slowdown to a
        # thread and keep our event loop responsive.
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            _wrap_render_errors,
            partial(
                invoke_render,
                module_zipfile,
                chroot_context=chroot_context,
                basedir=basedir,
                input_table=input_result.table,
                params=params,
                tab=tab,
                fetch_result=fetch_result,
                output_filename=output_path.name,
            ),
        )


async def execute_wfmodule(
    chroot_context: ChrootContext,
    workflow: Workflow,
    wf_module: WfModule,
    module_zipfile: Optional[ModuleZipfile],
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
    # may raise UnneededExecution
    result = await _render_wfmodule(
        chroot_context=chroot_context,
        workflow=workflow,
        wf_module=wf_module,
        module_zipfile=module_zipfile,
        raw_params=params,
        tab=tab,
        input_result=input_result,
        tab_results=tab_results,
        output_path=output_path,
    )

    # may raise UnneededExecution
    crr, output_delta = await _execute_wfmodule_save(workflow, wf_module, result)

    update = clientside.Update(
        steps={
            wf_module.id: clientside.StepUpdate(
                render_result=crr, module_slug=wf_module.module_id_name
            )
        }
    )
    await rabbitmq.send_update_to_workflow_clients(workflow.id, update)

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
