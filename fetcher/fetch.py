import asyncio
import contextlib
from datetime import timedelta
from functools import partial
import logging
import os
from pathlib import Path
import tempfile
from typing import Optional, Tuple
from django.conf import settings
from django.db import DatabaseError, InterfaceError
from django.utils import timezone
from cjwkernel.types import FetchResult, I18nMessage, Params, RenderError, TableMetadata
from cjworkbench.sync import database_sync_to_async
from cjworkbench.util import benchmark
from cjwstate import minio
from cjwstate.models import (
    CachedRenderResult,
    ModuleVersion,
    StoredObject,
    WfModule,
    Workflow,
)
from cjwstate.models.loaded_module import LoadedModule
from cjwstate import rendercache, storedobjects
from . import fetchprep, save


logger = logging.getLogger(__name__)


@database_sync_to_async
def _get_stored_object_and_input_cached_render_result(
    wf_module: WfModule
) -> Tuple[Optional[StoredObject], Optional[CachedRenderResult]]:
    try:
        # raises StoredObject.DoesNotExist
        stored_object = wf_module.stored_objects.get(
            stored_at=wf_module.stored_data_version
        )
    except StoredObject.DoesNotExist:
        stored_object = None

    try:
        # raises WfModule.DoesNotExist
        wf_module = WfModule.objects.get(
            tab_id=wf_module.tab_id,
            tab__is_deleted=False,
            order=wf_module.order - 1,
            is_deleted=False,
        )
        input_crr = wf_module.cached_render_result  # may be None
    except WfModule.DoesNotExist:
        input_crr = None

    return stored_object, input_crr


@contextlib.contextmanager
def open_stored_object_or_none(maybe_stored_object: Optional[StoredObject], error: str):
    if maybe_stored_object is None:
        yield None
    else:
        if error:
            errors = [RenderError(I18nMessage.TODO_i18n(error))]
        else:
            errors = []

        bucket = maybe_stored_object.bucket
        key = maybe_stored_object.key
        with tempfile.NamedTemporaryFile(prefix="last-fetch-result") as tf:
            path = Path(tf.name)
            if maybe_stored_object.size > 0:
                try:
                    minio.download(bucket, key, path)
                except FileNotFoundError:
                    # StoredObject does not exist
                    yield None
                    return

            yield FetchResult(path, errors)


@database_sync_to_async
def _get_wf_module(wf_module_id: int) -> Tuple[int, WfModule, Optional[ModuleVersion]]:
    """
    Query WfModule info, or raise WfModule.DoesNotExist.
    """
    wf_module = WfModule.objects.get(id=wf_module_id)
    # wf_module.workflow_id does a database access
    return (wf_module.workflow_id, wf_module)


@database_sync_to_async
def _get_loaded_module(wf_module: WfModule) -> Optional[LoadedModule]:
    """
    Query WfModule.module_version, then LoadedModule.for_module_version()
    """
    module_version = wf_module.module_version  # invokes DB query
    # .for_module_version() allows null
    return LoadedModule.for_module_version_sync(module_version)


@database_sync_to_async
def _update_next_update_time(wf_module, now):
    """Schedule next update, skipping missed updates if any."""
    tick = timedelta(
        seconds=max(wf_module.update_interval, settings.MIN_AUTOFETCH_INTERVAL)
    )

    try:
        with wf_module.workflow.cooperative_lock():
            wf_module.refresh_from_db()
            next_update = wf_module.next_update
            if next_update:
                while next_update <= now:
                    next_update += tick

            WfModule.objects.filter(id=wf_module.id).update(
                last_update_check=now, next_update=next_update
            )
    except Workflow.DoesNotExist:
        # [2019-05-27] `wf_module.workflow` throws `Workflow.DoesNotExist` if
        # the WfModule is deleted. This handler is for deleted-Workflow _and_
        # deleted-WfModule.
        pass


async def fetch_wf_module(workflow_id, wf_module, now):
    """Fetch `wf_module` and notify user of changes via email/websockets."""
    try:
        lm = await _get_loaded_module(wf_module)
        if lm is None:
            logger.info("fetch() deleted module '%s'", wf_module.module_id_name)
            result = FetchResult.from_error_deprecated(
                "Cannot fetch: module was deleted"
            )
            await save.save_result_if_changed(workflow_id, wf_module, result)
        else:
            stored_object, maybe_input_crr = await _get_stored_object_and_input_cached_render_result(
                wf_module
            )
            with contextlib.ExitStack() as ctx:
                if stored_object is None:
                    last_fetch_result = None
                else:
                    try:
                        last_fetch_path = ctx.enter_context(
                            storedobjects.downloaded_file(stored_object)
                        )
                        last_fetch_result = FetchResult(
                            last_fetch_path,
                            [RenderError(I18nMessage.TODO_i18n(wf_module.fetch_error))],
                        )
                    except FileNotFoundError:
                        last_fetch_result = None

                if maybe_input_crr is None:
                    input_parquet_path = None
                    input_metadata = TableMetadata()
                else:
                    try:
                        input_parquet_path = ctx.enter_context(
                            rendercache.downloaded_parquet_file
                        )
                        input_metadata = maybe_input_crr.table_metadata
                    except rendercache.CorruptCacheError:
                        # This is probably a race. That's okay.
                        input_parquet_path = None
                        input_metadata = TableMetadata()

                # Migrate params, so fetch() gets newest values
                params = lm.migrate_params(wf_module.params)
                # Clean params, so they're of the correct type
                params = Params(
                    fetchprep.clean_value(lm.param_schema, params, input_metadata)
                )

                with tempfile.NamedTemporaryFile(prefix="fetch-result") as tf:
                    path = Path(tf.name)
                    result = await asyncio.get_event_loop().run_in_executor(
                        None,
                        partial(
                            lm.fetch,
                            params=params,
                            secrets=wf_module.secrets,
                            last_fetch_result=last_fetch_result,
                            input_parquet_path=input_parquet_path,
                            output_path=path,
                        ),
                    )

                    await save.save_result_if_changed(workflow_id, wf_module, result)
    except asyncio.CancelledError:
        raise
    except Exception:
        # Log exceptions but keep going
        logger.exception(f"Error fetching {wf_module}")

    await _update_next_update_time(wf_module, now)


async def fetch(*, wf_module_id: int) -> None:
    try:
        (workflow_id, wf_module) = await _get_wf_module(wf_module_id)
    except WfModule.DoesNotExist:
        logger.info("Skipping fetch of deleted WfModule %d", wf_module_id)
        return

    now = timezone.now()
    # most exceptions caught elsewhere
    try:
        task = fetch_wf_module(workflow_id, wf_module, now)
        await benchmark(
            logger,
            task,
            "fetch_wf_module(%d, %d:%s)",
            workflow_id,
            wf_module_id,
            wf_module.module_id_name,
        )
    except DatabaseError:
        # Two possibilities:
        #
        # 1. There's a bug in module_dispatch_fetch. This may leave the event
        # loop's executor thread's database connection in an inconsistent
        # state. [2018-11-06 saw this on production.] The best way to clear
        # up the leaked, broken connection is to die. (Our parent process
        # should restart us, and RabbitMQ will give the job to someone
        # else.)
        #
        # 2. The database connection died (e.g., Postgres went away.) The
        # best way to clear up the leaked, broken connection is to die.
        # (Our parent process should restart us, and RabbitMQ will give the
        # job to someone else.)
        #
        # 3. There's some design flaw we haven't thought of, and we
        # shouldn't ever render this workflow. If this is the case, we're
        # doomed.
        #
        # If you're seeing this error that means there's a bug somewhere
        # _else_. If you're staring at a case-3 situation, please remember
        # that cases 1 and 2 are important, too.
        logger.exception("Fatal database error; exiting")
        os._exit(1)
    except InterfaceError:
        logger.exception("Fatal database error; exiting")
        os._exit(1)


async def handle_fetch(message):
    try:
        await fetch(**message)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Error during fetch")
