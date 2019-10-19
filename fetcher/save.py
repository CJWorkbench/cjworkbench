from pathlib import Path
from typing import Optional
from django.utils import timezone
import pandas as pd
from pandas.util import hash_pandas_object
import pyarrow
from cjworkbench.sync import database_sync_to_async
from cjwkernel import parquet
from cjwkernel.types import FetchResult
from cjwstate import commands, storedobjects
from server import websockets
from cjwstate.models import StoredObject, WfModule, Workflow
from cjwstate.models.commands import ChangeDataVersionCommand


def hash_table(table: pd.DataFrame) -> str:
    """Build a hash useful in comparing data frames for equality."""
    h = hash_pandas_object(table).sum()  # xor would be nice, but whatevs
    h = h if h > 0 else -h  # stay positive (sum often overflows)
    return str(h)


def parquet_file_to_pandas(path: Path) -> pd.DataFrame:
    if path.stat().st_size == 0:
        return pd.DataFrame()
    else:
        with parquet.open_as_mmapped_arrow(path) as arrow_table:
            return arrow_table.to_pandas(
                date_as_object=False,
                deduplicate_objects=True,
                ignore_metadata=True,
                categories=[
                    column_name.encode("utf-8")
                    for column_name, column in zip(
                        arrow_table.column_names, arrow_table.columns
                    )
                    if hasattr(column.type, "dictionary")
                ],
            )  # TODO ensure dictionaries stay dictionaries


def read_dataframe_from_stored_object(
    stored_object: StoredObject
) -> Optional[pd.DataFrame]:
    """
    Read DataFrame from StoredObject.

    Return None if:

    * there is no file on minio
    * the file on minio cannot be read

    TODO return a pyarrow.Table instead.
    """
    if stored_object.bucket == "":  # ages ago, "empty" meant bucket='', key=''
        return pd.DataFrame()
    try:
        with storedobjects.downloaded_file(stored_object) as path:
            return parquet_file_to_pandas(path)
    except (FileNotFoundError, pyarrow.ArrowIOError):
        return None


def _store_fetched_table_if_different(
    workflow: Workflow, wf_module: WfModule, result: FetchResult
) -> Optional[timezone.datetime]:
    # Called within _maybe_add_version()
    #
    # For backwards-compat, we use an extremely inefficient method of
    # deciding whether two fetch results are equivalent. We should probably
    # delegate the hashing function to the modules themselves ... and default
    # to a sha1 of the file data. Transitioning all our existing fetch results
    # will be tricky.
    table = parquet_file_to_pandas(result.path)
    hash = hash_table(table)
    old_so = wf_module.stored_objects.order_by("-stored_at").first()
    if (
        old_so is not None
        # Fast: hashes differ, so we don't need to read the table
        and hash == old_so.hash
        # Slow: compare files. Expensive: reads a file from S3, holds
        # both DataFrames in RAM, uses lots of CPU.
        and table.equals(read_dataframe_from_stored_object(old_so))
    ):
        # `table` is identical to what was in `old_so`.
        return None

    stored_object = storedobjects.create_stored_object(
        workflow.id, wf_module.id, result.path, hash
    )
    storedobjects.enforce_storage_limits(wf_module)
    return stored_object.stored_at


@database_sync_to_async
def _maybe_add_version(
    workflow: Workflow, wf_module: WfModule, maybe_result: Optional[FetchResult]
) -> Optional[timezone.datetime]:
    """
    Apply `result` to `wf_module`.

    Set `is_busy`, `fetch_error` and `last_update_check`.

    Write a new `StoredObject` and returns its `datetime` if the input
    `maybe_result` is non-``None`` and the result isn't the same as the
    previous one. Che caller may create a ``ChangeDataVersionCommand`` to set
    `wf_module`'s next data version.

    If the input Workflow or WfModule is deleted, return ``None``.
    """
    # Use Django `update_fields` to only write the fields we're
    # editing.  That's because every value in `wf_module` might be
    # stale, so we must ignore those stale values.
    fields = {"is_busy": False, "last_update_check": timezone.now()}
    if maybe_result is not None:
        if maybe_result.errors:
            if maybe_result.errors[0].message.id != "TODO_i18n":
                raise RuntimeError("TODO handle i18n-ready fetch-result errors")
            elif maybe_result.errors[0].quick_fixes:
                raise RuntimeError("TODO handle quick fixes from fetches")
            else:
                fields["fetch_error"] = maybe_result.errors[0].message.args["text"]
        else:
            fields["fetch_error"] = ""

    try:
        with wf_module.workflow.cooperative_lock():
            wf_module.refresh_from_db()  # raise WfModule.DoesNotExist
            if wf_module.is_deleted or wf_module.tab.is_deleted:
                return None

            if maybe_result is not None:
                # TODO store result error, too. Actually, nix StoredObject
                # entirely and let fetch methods return arbitrary blobs.
                version_added = _store_fetched_table_if_different(
                    workflow, wf_module, maybe_result
                )
            else:
                version_added = None

            for k, v in fields.items():
                setattr(wf_module, k, v)
            wf_module.save(update_fields=fields.keys())

            return version_added
    except (Workflow.DoesNotExist, WfModule.DoesNotExist):
        return None


@database_sync_to_async
def get_wf_module_workflow(wf_module: WfModule) -> Workflow:
    return wf_module.workflow  # does a database query


async def save_result_if_changed(
    workflow_id: int, wf_module: WfModule, new_result: Optional[FetchResult]
) -> None:
    """
    Store fetched table, if it is a change from `wf_module`'s existing data.

    "Change" here means either a changed table or changed error message.

    Set `fetch_error` to `new_result.error`.

    Set wf_module.is_busy to False.

    Set wf_module.last_update_check.

    Create (and run) a ChangeDataVersionCommand if something changed. This
    will kick off an execute cycle, which will render each module and email the
    owner if data has changed and notifications are enabled.

    Otherwise, notify the user of the wf_module.last_update_check.

    Call with `new_result=None` to indicate that a fetch is finished and
    guarantee not to add a new version.
    """
    try:
        workflow = await get_wf_module_workflow(wf_module)
    except Workflow.DoesNotExist:
        return  # there's nothing more to do

    version_added = await _maybe_add_version(workflow, wf_module, new_result)

    if version_added:
        # Don't send_delta_async. wf_module.last_relevant_delta_id hasn't been
        # set, so at this point the module would appear to be "ready". (See
        # https://www.pivotaltracker.com/story/show/161863167 for an example.)
        # Instead, trust ChangeDataVersionCommand to update `is_busy` and
        # `fetch_error`.
        #
        # Rephrased:
        #
        # * Right here, the user sees "busy" (is_busy=True, cache=fresh)
        # * After the next line of code, the user _still_sees "busy"
        #   (is_busy=False, cache=stale)
        # * Later, the user will see "ok" (is_busy=False, cache=fresh)
        await commands.do(
            ChangeDataVersionCommand,
            workflow=workflow,
            wf_module=wf_module,
            new_version=version_added,
        )
    else:
        last_update_check = wf_module.last_update_check
        if last_update_check:
            last_update_check = last_update_check.isoformat()

        await websockets.ws_client_send_delta_async(
            workflow_id,
            {
                "updateWfModules": {
                    str(wf_module.id): {
                        "is_busy": wf_module.is_busy,
                        "fetch_error": wf_module.fetch_error,
                        "last_update_check": last_update_check,
                    }
                }
            },
        )
