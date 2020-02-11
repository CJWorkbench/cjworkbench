import asyncio
import contextlib
from datetime import timedelta
import logging
import os
from pathlib import Path
import time
from typing import Any, ContextManager, Dict, List, NamedTuple, Optional, Union
from django.conf import settings
from django.db import DatabaseError, InterfaceError
from django.utils import timezone
from cjwkernel.chroot import EDITABLE_CHROOT, ChrootContext
from cjwkernel.errors import ModuleError, format_for_user_debugging
from cjwkernel.types import FetchResult, I18nMessage, Params, RenderError, TableMetadata
from cjworkbench.sync import database_sync_to_async
from cjwstate.models import CachedRenderResult, StoredObject, WfModule, Workflow
from cjwstate.models.module_registry import MODULE_REGISTRY
from cjwstate.modules.types import ModuleZipfile
import cjwstate.params
from cjwstate import rendercache, storedobjects
import fetcher.secrets
from . import fetchprep, save, versions


logger = logging.getLogger(__name__)


def invoke_fetch(
    module_zipfile: ModuleZipfile,
    *,
    chroot_context: ChrootContext,
    basedir: Path,
    params: Params,
    secrets: Dict[str, Any],
    last_fetch_result: Optional[FetchResult],
    input_parquet_filename: Optional[str],
    output_filename: str,
) -> FetchResult:
    """
    Use kernel to invoke module `fetch(...)` method and build a `FetchResult`.

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
        ("wf_module", WfModule),
        ("module_zipfile", Optional[ModuleZipfile]),
        ("migrated_params_or_error", Union[Dict[str, Any], ModuleError]),
        ("stored_object", Optional[StoredObject]),
        ("input_cached_render_result", Optional[CachedRenderResult]),
    ],
)


@database_sync_to_async
def load_database_objects(workflow_id: int, wf_module_id: int) -> DatabaseObjects:
    """
    Query WfModule info.
    
    Raise `WfModule.DoesNotExist` or `Workflow.DoesNotExist` if the step was
    deleted.

    Catch a `ModuleError` from migrate_params() and return it as part of the
    `DatabaseObjects`.
    """
    with Workflow.lookup_and_cooperative_lock(id=workflow_id) as workflow_lock:
        # raise WfModule.DoesNotExist
        wf_module = WfModule.live_in_workflow(workflow_lock.workflow).get(
            id=wf_module_id
        )

        # module_zipfile
        try:
            module_zipfile = MODULE_REGISTRY.latest(wf_module.module_id_name)
        except KeyError:
            module_zipfile = None

        # migrated_params_or_error
        if module_zipfile is None:
            migrated_params_or_error = {}
        else:
            try:
                migrated_params_or_error = cjwstate.params.get_migrated_params(
                    wf_module, module_zipfile=module_zipfile
                )  # raise ModuleError
            except ModuleError as err:
                migrated_params_or_error = err

        # stored_object
        try:
            stored_object = wf_module.stored_objects.get(
                stored_at=wf_module.stored_data_version
            )
        except StoredObject.DoesNotExist:
            stored_object = None

        # input_crr
        try:
            # raise WfModule.DoesNotExist -- but we'll catch this one
            prev_module = wf_module.tab.live_wf_modules.get(order=wf_module.order - 1)
            input_crr = prev_module.cached_render_result  # may be None
        except WfModule.DoesNotExist:
            input_crr = None

        return DatabaseObjects(
            wf_module,
            module_zipfile,
            migrated_params_or_error,
            stored_object,
            input_crr,
        )


@database_sync_to_async
def update_next_update_time(workflow_id, wf_module, now):
    """Schedule next update, skipping missed updates if any."""

    tick = timedelta(
        seconds=max(wf_module.update_interval, settings.MIN_AUTOFETCH_INTERVAL)
    )

    try:
        with Workflow.lookup_and_cooperative_lock(id=workflow_id):
            wf_module.refresh_from_db()
            next_update = wf_module.next_update
            if next_update:
                while next_update <= now:
                    next_update += tick

            WfModule.objects.filter(id=wf_module.id).update(
                last_update_check=now, next_update=next_update
            )
    except (WfModule.DoesNotExist, Workflow.DoesNotExist):
        # [2019-05-27] `wf_module.workflow` throws `Workflow.DoesNotExist` if
        # the WfModule is deleted. This handler is for deleted-Workflow _and_
        # deleted-WfModule.
        pass


def user_visible_bug_fetch_result(output_path: Path, message: str) -> FetchResult:
    output_path.write_bytes(b"")
    return FetchResult(
        path=output_path,  # empty
        errors=[
            RenderError(
                I18nMessage.trans(
                    "py.fetcher.fetch.user_visible_bug_fetch_result",
                    default=(
                        "Something unexpected happened. We have been notified and are "
                        "working to fix it. If this persists, contact us. Error code: {message}"
                    ),
                    args={"message": message},
                )
            )
        ],
    )


DownloadedCachedRenderResult = NamedTuple(
    "DownloadedCachedRenderResult",
    [("maybe_path", Optional[Path]), ("table_metadata", TableMetadata)],
)


def _download_cached_render_result(
    ctx: contextlib.ExitStack, maybe_crr: Optional[CachedRenderResult], dir: Path
) -> DownloadedCachedRenderResult:
    if maybe_crr is None:
        return DownloadedCachedRenderResult(None, TableMetadata())
    else:
        try:
            parquet_path = ctx.enter_context(
                rendercache.downloaded_parquet_file(maybe_crr, dir=dir)
            )
            return DownloadedCachedRenderResult(parquet_path, maybe_crr.table_metadata)
        except rendercache.CorruptCacheError:
            # This is probably a race. That's okay. Treat missing
            # cache as, "there is no input". (This is user-visible
            # but likely uncommon.)
            return DownloadedCachedRenderResult(None, TableMetadata())


def _stored_object_to_fetch_result(
    ctx: contextlib.ExitStack,
    stored_object: Optional[StoredObject],
    wf_module_fetch_error: str,
    wf_module_fetch_errors: List[RenderError],
    dir: Path,
) -> Optional[FetchResult]:
    """
    Given a StoredObject (or None), return a FetchResult (or None).

    This cannot error. Any errors lead to a `None` return value.
    """
    if stored_object is None:
        return None
    else:
        try:
            last_fetch_path = ctx.enter_context(
                storedobjects.downloaded_file(stored_object, dir=dir)
            )
            if wf_module_fetch_error:
                # TODO_i18n once wf_module.fetch_error is always-empty
                errors = [RenderError(I18nMessage.TODO_i18n(wf_module_fetch_error))]
            else:
                errors = wf_module_fetch_errors
            return FetchResult(last_fetch_path, errors)
        except FileNotFoundError:
            return None


def fetch_or_wrap_error(
    ctx: contextlib.ExitStack,
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
    """
    Fetch, and do not raise any exceptions worth catching.

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
                    I18nMessage.trans(
                        "py.fetcher.fetch.fetch_or_wrap_error.no_loaded_module",
                        default="Cannot fetch: module was deleted",
                    )
                )
            ],
        )
    module_spec = module_zipfile.get_spec()
    param_schema = module_spec.get_param_schema()

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
        ctx, maybe_input_crr, dir=basedir
    )

    # Clean params, so they're of the correct type. (This can't error.)
    params = Params(
        fetchprep.clean_value(param_schema, migrated_params, input_metadata)
    )

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


@contextlib.contextmanager
def crash_on_database_error() -> ContextManager[None]:
    """
    Yield, and if the inner block crashes, sys._exit(1).

    DatabaseError and InterfaceError from Django can mean:
    
    1. There's a bug in fetch() or its deps. Such bugs can permanently break
    the event loop's executor thread's database connection.
    [2018-11-06 saw this on production.] The best way to clear up the leaked,
    broken connection is to die. (Our parent process should restart us, and
    RabbitMQ will give the job to someone else.)
    
    2. The database connection died (e.g., Postgres went away.) This should
    be rare -- e.g., when upgrading the database -- and it's okay to email us
    and die in this case. (Our parent process should restart us, and RabbitMQ
    will give the job to someone else.)
    
    3. There's some design flaw we haven't thought of, and we shouldn't ever
    render this workflow. If this is the case, we're doomed.
    
    If you're seeing this error that means there's a bug somewhere _else_. If
    you're staring at a case-3 situation, please remember that cases 1 and 2
    are important, too.
    """
    try:
        yield
    except (DatabaseError, InterfaceError):
        logger.exception("Fatal database error; exiting")
        os._exit(1)


async def fetch(
    *, workflow_id: int, wf_module_id: int, now: Optional[timezone.datetime] = None
) -> None:
    # 1. Load database objects
    #    - missing WfModule? Return prematurely
    #    - database error? _exit(1)
    #    - module_zipfile missing/invalid? user-visible error
    #    - migrate_params() fails? user-visible error
    # 2. Calculate result
    #    2a. Build fetch kwargs
    #    2b. Call fetch (no errors possible -- LoadedModule catches them)
    # 3. Save result (and send delta)
    #    - database errors? _exit(1)
    #    - other error (bug in `save`)? Log exception and ignore
    # 4. Update WfModule last-fetch time
    #    - database errors? _exit(1)
    with crash_on_database_error():
        logger.info(
            "begin fetch(workflow_id=%d, wf_module_id=%d)", workflow_id, wf_module_id
        )

        try:
            (
                wf_module,
                module_zipfile,
                migrated_params,
                stored_object,
                input_crr,
            ) = await load_database_objects(workflow_id, wf_module_id)
        except (Workflow.DoesNotExist, WfModule.DoesNotExist):
            logger.info(
                "Skipping fetch of deleted WfModule %d-%d", workflow_id, wf_module_id
            )
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
            module_spec.param_fields, wf_module.secrets
        )

    if now is None:
        now = timezone.now()

    with contextlib.ExitStack() as ctx:
        chroot_context = ctx.enter_context(EDITABLE_CHROOT.acquire_context())
        basedir = ctx.enter_context(chroot_context.tempdir_context(prefix="fetch-"))
        output_path = ctx.enter_context(
            chroot_context.tempfile_context(prefix="fetch-result-", dir=basedir)
        )
        # get last_fetch_result (This can't error.)
        last_fetch_result = _stored_object_to_fetch_result(
            ctx,
            stored_object,
            wf_module.fetch_error,
            wf_module.fetch_errors or [],  # TODO nix "or" when NOT NULL
            dir=basedir,
        )
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            fetch_or_wrap_error,
            ctx,
            chroot_context,
            basedir,
            wf_module.module_id_name,
            module_zipfile,
            migrated_params,
            secrets,
            last_fetch_result,
            input_crr,
            output_path,
        )

        try:
            with crash_on_database_error():
                if last_fetch_result is not None and versions.are_fetch_results_equal(
                    last_fetch_result, result
                ):
                    await save.mark_result_unchanged(workflow_id, wf_module, now)
                else:
                    await save.create_result(workflow_id, wf_module, result, now)
        except asyncio.CancelledError:
            raise
        except Exception:
            # Log exceptions but keep going.
            # TODO [adamhooper, 2019-09-12] really? I think we don't want this.
            # Make `fetch.save() robust, then nix this handler
            logger.exception(f"Error fetching {wf_module}")

    with crash_on_database_error():
        await update_next_update_time(workflow_id, wf_module, now)


async def handle_fetch(message):
    try:
        await fetch(**message)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Error during fetch")
