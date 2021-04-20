import asyncio
import contextlib
import datetime
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Union

from django.conf import settings

import cjwstate.params
import fetcher.secrets
from cjwkernel.chroot import EDITABLE_CHROOT, ChrootContext
from cjwkernel.errors import ModuleError, format_for_user_debugging
from cjwkernel.i18n import trans
from cjwkernel.types import FetchResult, RenderError, TableMetadata
from cjworkbench.sync import database_sync_to_async
from cjwstate.models import CachedRenderResult, StoredObject, Step, Workflow
from cjwstate.models.module_registry import MODULE_REGISTRY
from cjwstate.modules.types import ModuleZipfile
from cjwstate import rendercache, storedobjects

from . import fetchprep, save, versions


logger = logging.getLogger(__name__)


def invoke_fetch(
    module_zipfile: ModuleZipfile,
    *,
    chroot_context: ChrootContext,
    basedir: Path,
    params: Dict[str, Any],
    secrets: Dict[str, Any],
    last_fetch_result: Optional[FetchResult],
    input_parquet_filename: Optional[str],
    output_filename: str,
) -> FetchResult:
    """Use kernel to invoke module `fetch(...)` method and build a `FetchResult`.

    Raise `ModuleError` on error. (This is usually the module author's fault.)

    Log any ModuleError. Also log success.

    This synchronous method can be slow for complex modules, large datasets
    or slow network requests. Consider calling it from an executor.
    """
    time1 = time.time()
    status = "???"

    logger.info("%s:fetch() begin", module_zipfile.path.name)
    compiled_module = module_zipfile.compile_code_without_executing()

    try:
        ret = cjwstate.modules.kernel.fetch(
            compiled_module=compiled_module,
            chroot_context=chroot_context,
            basedir=basedir,
            params=params,
            secrets=secrets,
            last_fetch_result=last_fetch_result,
            input_parquet_filename=input_parquet_filename,
            output_filename=output_filename,
        )
        status = "%0.1fMB" % (ret.path.stat().st_size / 1024 / 1024)
        return ret
    except ModuleError as err:
        logger.exception("Exception in %s:fetch", module_zipfile.path.name)
        status = type(err).__name__
        raise
    finally:
        time2 = time.time()
        logger.info(
            "%s:fetch() => %s in %dms",
            module_zipfile.path.name,
            status,
            int((time2 - time1) * 1000),
        )


DatabaseObjects = NamedTuple(
    "DatabaseObjects",
    [
        ("step", Step),
        ("module_zipfile", Optional[ModuleZipfile]),
        ("migrated_params_or_error", Union[Dict[str, Any], ModuleError]),
        ("stored_object", Optional[StoredObject]),
        ("input_cached_render_result", Optional[CachedRenderResult]),
    ],
)


@database_sync_to_async
def load_database_objects(workflow_id: int, step_id: int) -> DatabaseObjects:
    """Query Step info.

    Raise `Step.DoesNotExist` or `Workflow.DoesNotExist` if the step was
    deleted.

    Catch a `ModuleError` from migrate_params() and return it as part of the
    `DatabaseObjects`.
    """
    with Workflow.lookup_and_cooperative_lock(id=workflow_id) as workflow_lock:
        # raise Step.DoesNotExist
        step = Step.live_in_workflow(workflow_lock.workflow).get(id=step_id)

        # module_zipfile
        try:
            module_zipfile = MODULE_REGISTRY.latest(step.module_id_name)
        except KeyError:
            module_zipfile = None

        # migrated_params_or_error
        if module_zipfile is None:
            migrated_params_or_error = {}
        else:
            try:
                migrated_params_or_error = cjwstate.params.get_migrated_params(
                    step, module_zipfile=module_zipfile
                )  # raise ModuleError
            except ModuleError as err:
                migrated_params_or_error = err

        # stored_object
        try:
            stored_object = step.stored_objects.get(stored_at=step.stored_data_version)
        except StoredObject.DoesNotExist:
            stored_object = None

        # input_crr
        try:
            # raise Step.DoesNotExist -- but we'll catch this one
            prev_module = step.tab.live_steps.get(order=step.order - 1)
            input_crr = prev_module.cached_render_result  # may be None
        except Step.DoesNotExist:
            input_crr = None

        return DatabaseObjects(
            step,
            module_zipfile,
            migrated_params_or_error,
            stored_object,
            input_crr,
        )


@database_sync_to_async
def update_next_update_time(workflow_id, step, now):
    """Schedule next update, skipping missed updates if any."""

    tick = datetime.timedelta(
        seconds=max(step.update_interval, settings.MIN_AUTOFETCH_INTERVAL)
    )

    try:
        with Workflow.lookup_and_cooperative_lock(id=workflow_id):
            step.refresh_from_db()
            next_update = step.next_update
            if next_update:
                while next_update <= now:
                    next_update += tick

            Step.objects.filter(id=step.id).update(
                last_update_check=now, next_update=next_update
            )
    except (Step.DoesNotExist, Workflow.DoesNotExist):
        # [2019-05-27] `step.workflow` throws `Workflow.DoesNotExist` if
        # the Step is deleted. This handler is for deleted-Workflow _and_
        # deleted-Step.
        pass


def user_visible_bug_fetch_result(output_path: Path, message: str) -> FetchResult:
    output_path.write_bytes(b"")
    return FetchResult(
        path=output_path,  # empty
        errors=[
            RenderError(
                trans(
                    "py.fetcher.fetch.user_visible_bug_during_fetch",
                    default="Something unexpected happened. We have been notified and are "
                    "working to fix it. If this persists, contact us. Error code: {message}",
                    arguments={"message": message},
                )
            )
        ],
    )


DownloadedCachedRenderResult = NamedTuple(
    "DownloadedCachedRenderResult",
    [("maybe_path", Optional[Path]), ("table_metadata", TableMetadata)],
)


def _download_cached_render_result(
    exit_stack: contextlib.ExitStack, maybe_crr: Optional[CachedRenderResult], dir: Path
) -> DownloadedCachedRenderResult:
    if maybe_crr is None:
        return DownloadedCachedRenderResult(None, TableMetadata())
    else:
        try:
            parquet_path = exit_stack.enter_context(
                rendercache.downloaded_parquet_file(maybe_crr, dir=dir)
            )
            return DownloadedCachedRenderResult(parquet_path, maybe_crr.table_metadata)
        except rendercache.CorruptCacheError:
            # This is probably a race. That's okay. Treat missing
            # cache as, "there is no input". (This is user-visible
            # but likely uncommon.)
            return DownloadedCachedRenderResult(None, TableMetadata())


def _stored_object_to_fetch_result(
    exit_stack: contextlib.ExitStack,
    stored_object: Optional[StoredObject],
    step_fetch_errors: List[RenderError],
    dir: Path,
) -> Optional[FetchResult]:
    """Given a StoredObject (or None), return a FetchResult (or None).

    This cannot error. Any errors lead to a `None` return value.
    """
    if stored_object is None:
        return None
    else:
        try:
            last_fetch_path = exit_stack.enter_context(
                storedobjects.downloaded_file(stored_object, dir=dir)
            )
            return FetchResult(last_fetch_path, step_fetch_errors)
        except FileNotFoundError:
            return None


def fetch_or_wrap_error(
    exit_stack: contextlib.ExitStack,
    chroot_context: ChrootContext,
    basedir: Path,
    module_id_name: str,
    module_zipfile: ModuleZipfile,
    migrated_params_or_error: Union[Dict[str, Any], ModuleError],
    secrets: Dict[str, Any],
    last_fetch_result: Optional[FetchResult],
    maybe_input_crr: Optional[CachedRenderResult],
    output_path: Path,
):
    """Fetch, and do not raise any exceptions worth catching.

    Exceptions are wrapped -- the result is a FetchResult with `.errors`.

    This function is slow indeed. Perhaps call it from
    EventLoop.run_in_executor(). (Why not make it async? Because all the logic
    inside -- compile module, fetch() -- is sandboxed, meaning it gets its own
    processes. We may eventually avoid asyncio entirely in `fetcher`.

    These problems are all handled:

    * Module was deleted (`module_zipfile is None`)
    * Module times out (`cjwkernel.errors.ModuleTimeoutError`), in `fetch()`.
    * Module crashes (`cjwkernel.errors.ModuleExitedError`), in `fetch()`.
    * migrated_params_or_error is a `ModuleError`
    * migrated_params_or_error is invalid (`ValueError`)
    * input_crr points to a nonexistent file (`FileNotFoundError`)
    """
    # module_zipfile=None is allowed
    if module_zipfile is None:
        logger.info("fetch() deleted module '%s'", module_id_name)
        return FetchResult(
            output_path,
            [
                RenderError(
                    trans(
                        "py.fetcher.fetch.no_loaded_module",
                        default="Cannot fetch: module was deleted",
                    )
                )
            ],
        )
    module_spec = module_zipfile.get_spec()
    param_schema = module_spec.param_schema

    if isinstance(migrated_params_or_error, ModuleError):
        # raise the exception so we can log it
        try:
            raise migrated_params_or_error
        except ModuleError:
            # We'll always get here
            logger.exception(
                "%s:migrate_params() raised error", module_zipfile.path.name
            )
        return user_visible_bug_fetch_result(
            output_path, format_for_user_debugging(migrated_params_or_error)
        )
    migrated_params = migrated_params_or_error

    try:
        param_schema.validate(migrated_params)
    except ValueError:
        logger.exception(
            "Invalid return value from %s:migrate_params()", module_zipfile.path.name
        )
        return user_visible_bug_fetch_result(
            output_path,
            "%s:migrate_params() output invalid params" % module_zipfile.path.name,
        )

    # get input_metadata, input_parquet_path. (This can't error.)
    input_parquet_path, input_metadata = _download_cached_render_result(
        exit_stack, maybe_input_crr, dir=basedir
    )

    # Clean params, so they're of the correct type. (This can't error.)
    params = fetchprep.clean_value(param_schema, migrated_params, input_metadata)

    # actually fetch
    try:
        return invoke_fetch(
            module_zipfile,
            chroot_context=chroot_context,
            basedir=basedir,
            params=params,
            secrets=secrets,
            last_fetch_result=last_fetch_result,
            input_parquet_filename=(
                None if input_parquet_path is None else input_parquet_path.name
            ),
            output_filename=output_path.name,
        )
    except ModuleError as err:
        logger.exception("Error calling %s:fetch()", module_zipfile.path.name)
        return user_visible_bug_fetch_result(
            output_path, format_for_user_debugging(err)
        )


async def fetch(
    *, workflow_id: int, step_id: int, now: Optional[datetime.datetime] = None
) -> None:
    # 1. Load database objects
    #    - missing Step? Return prematurely
    #    - database error? Raise
    #    - module_zipfile missing/invalid? user-visible error
    #    - migrate_params() fails? user-visible error
    # 2. Calculate result
    #    2a. Build fetch kwargs
    #    2b. Call fetch (no errors possible -- LoadedModule catches them)
    # 3. Save result (and send delta)
    #    - database errors? Raise
    #    - rabbitmq errors? Raise
    #    - other error (bug in `save`)? Raise
    # 4. Update Step last-fetch time
    #    - database errors? Raise
    logger.info("begin fetch(workflow_id=%d, step_id=%d)", workflow_id, step_id)

    try:
        (
            step,
            module_zipfile,
            migrated_params,
            stored_object,
            input_crr,
        ) = await load_database_objects(workflow_id, step_id)
    except (Workflow.DoesNotExist, Step.DoesNotExist):
        logger.info("Skipping fetch of deleted Step %d-%d", workflow_id, step_id)
        return

    # Prepare secrets -- mangle user values so modules have all they need.
    #
    # This can involve, e.g., HTTP request to OAuth2 token servers.
    #
    # TODO unit-test this code path
    if module_zipfile is None:
        secrets = {}
    else:
        module_spec = module_zipfile.get_spec()
        secrets = await fetcher.secrets.prepare_secrets(
            module_spec.param_fields, step.secrets
        )

    if now is None:
        now = datetime.datetime.now()

    with contextlib.ExitStack() as exit_stack:
        chroot_context = exit_stack.enter_context(EDITABLE_CHROOT.acquire_context())
        basedir = exit_stack.enter_context(
            chroot_context.tempdir_context(prefix="fetch-")
        )
        output_path = exit_stack.enter_context(
            chroot_context.tempfile_context(prefix="fetch-result-", dir=basedir)
        )
        # get last_fetch_result (This can't error.)
        last_fetch_result = _stored_object_to_fetch_result(
            exit_stack, stored_object, step.fetch_errors, dir=basedir
        )
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            fetch_or_wrap_error,
            exit_stack,
            chroot_context,
            basedir,
            step.module_id_name,
            module_zipfile,
            migrated_params,
            secrets,
            last_fetch_result,
            input_crr,
            output_path,
        )

        if last_fetch_result is not None and versions.are_fetch_results_equal(
            last_fetch_result, result
        ):
            await save.mark_result_unchanged(workflow_id, step, now)
        else:
            await save.create_result(workflow_id, step, result, now)

    await update_next_update_time(workflow_id, step, now)


async def handle_fetch(message):
    await fetch(**message)
