import datetime
import io
import json
import math
import re
import selectors
import subprocess
from typing import Any, Dict, List
from asgiref.sync import async_to_sync
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import (
    FileResponse,
    HttpRequest,
    HttpResponse,
    Http404,
    HttpResponseNotFound,
    JsonResponse,
)
from django.shortcuts import get_object_or_404
from django.utils.cache import add_never_cache_headers
from django.views.decorators.clickjacking import xframe_options_exempt
import numpy as np
import pyarrow as pa
from rest_framework import status
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from cjwkernel.types import Column, ColumnType
from cjwstate.rendercache import (
    CorruptCacheError,
    downloaded_parquet_file,
    open_cached_render_result,
    read_cached_render_result_slice_as_text,
)
from cjwstate.models import Tab, WfModule, Workflow
from cjwstate.modules.loaded_module import module_get_html_bytes
from server import rabbitmq


_MaxNRowsPerRequest = 300


def _with_wf_module_for_read(fn):
    """
    Decorate: `fn(request, wf_module_id, ...)` becomes `fn(request, wf_module, ...)`

    The inner function will be wrapped in a cooperative lock.

    The inner function will raise Http404 if pk is not found in the database,
    or PermissionDenied if the person requesting does not have read access.
    """

    def inner(request: HttpRequest, wf_module_id: int, *args, **kwargs):
        # TODO simplify this a ton by putting `workflow` in the URL. That way,
        # we can lock it _before_ we query it, so we won't have to check any of
        # the zillions of races herein.
        wf_module = get_object_or_404(WfModule, id=wf_module_id, is_deleted=False)
        try:
            # raise Tab.DoesNotExist, Workflow.DoesNotExist
            workflow = wf_module.workflow
            if workflow is None:
                raise Http404()  # race: workflow is gone

            # raise Workflow.DoesNotExist
            with workflow.cooperative_lock() as workflow_lock:
                if not workflow_lock.workflow.request_authorized_read(request):
                    raise PermissionDenied()

                wf_module.refresh_from_db()  # raise WfModule.DoesNotExist
                if wf_module.is_deleted or wf_module.tab.is_deleted:
                    raise Http404()  # race: WfModule/Tab deleted

            return fn(request, wf_module, *args, **kwargs)
        except (Workflow.DoesNotExist, Tab.DoesNotExist, WfModule.DoesNotExist):
            raise Http404()  # race: tab/wfmodule was deleted

    return inner


# ---- render / input / livedata ----
# These endpoints return actual table data


TimestampUnits = {"us": 1000000, "s": 1, "ms": 1000, "ns": 1000000000}  # most common


# Helper method that produces json output for a table + start/end row
# Also silently clips row indices
# Now reading a maximum of 101 columns directly from cache parquet
def _make_render_tuple(cached_result, startrow=None, endrow=None):
    """Build (startrow, endrow, json_rows) data."""

    if startrow is None:
        startrow = 0
    startrow = max(0, startrow)
    if endrow is None:
        endrow = startrow + _MaxNRowsPerRequest
    endrow = min(
        cached_result.table_metadata.n_rows, endrow, startrow + _MaxNRowsPerRequest
    )

    # raise CorruptCacheError
    record_json = read_cached_render_result_slice_as_text(
        cached_result,
        "json",
        # Return one row more than configured, so the client knows there
        # are "too many rows".
        only_columns=range(settings.MAX_COLUMNS_PER_CLIENT_REQUEST + 1),
        only_rows=range(startrow, endrow),
    )
    return (startrow, endrow, record_json)


def int_or_none(x):
    return int(x) if x is not None else None


# /render: return output table of this module
@api_view(["GET"])
@renderer_classes((JSONRenderer,))
@_with_wf_module_for_read
def wfmodule_render(request: HttpRequest, wf_module: WfModule, format=None):
    # Get first and last row from query parameters, or default to all if not
    # specified
    try:
        startrow = int_or_none(request.GET.get("startrow"))
        endrow = int_or_none(request.GET.get("endrow"))
    except ValueError:
        return Response(
            {"message": "bad row number", "status_code": 400},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with wf_module.workflow.cooperative_lock():
        wf_module.refresh_from_db()
        cached_result = wf_module.cached_render_result
        if cached_result is None:
            # assume we'll get another request after execute finishes
            return JsonResponse({"start_row": 0, "end_row": 0, "rows": []})

        try:
            startrow, endrow, record_json = _make_render_tuple(
                cached_result, startrow, endrow
            )
        except CorruptCacheError:
            # assume we'll get another request after execute finishes
            return JsonResponse({"start_row": 0, "end_row": 0, "rows": []})

    data = '{"start_row":%d,"end_row":%d,"rows":%s}' % (startrow, endrow, record_json)
    response = HttpResponse(
        data.encode("utf-8"), content_type="application/json", charset="utf-8"
    )
    add_never_cache_headers(response)
    return response


_html_head_start_re = re.compile(rb"<\s*head[^>]*>", re.IGNORECASE)


@api_view(["GET"])
@xframe_options_exempt
@_with_wf_module_for_read
def wfmodule_output(request: HttpRequest, wf_module: WfModule, format=None):
    html = module_get_html_bytes(wf_module.module_version)
    return HttpResponse(content=html)


@api_view(["GET"])
@renderer_classes((JSONRenderer,))
@_with_wf_module_for_read
def wfmodule_embeddata(request: HttpRequest, wf_module: WfModule):
    # Speedy bypassing of locks: we don't care if we get out-of-date data
    # because we assume the client will re-request when it gets a new
    # cached_render_result_delta_id.
    try:
        result_json = json.loads(
            bytes(wf_module.cached_render_result_json), encoding="utf-8"
        )
    except ValueError:
        result_json = None

    return JsonResponse(result_json, safe=False)


@api_view(["GET"])
@renderer_classes((JSONRenderer,))
@_with_wf_module_for_read
def wfmodule_value_counts(request: HttpRequest, wf_module: WfModule):
    try:
        colname = request.GET["column"]
    except KeyError:
        return JsonResponse({"error": 'Missing a "column" parameter'}, status=400)

    if not colname:
        # User has not yet chosen a column. Empty response.
        return JsonResponse({"values": {}})

    cached_result = wf_module.cached_render_result
    if cached_result is None:
        # assume we'll get another request after execute finishes
        return JsonResponse({"values": {}})

    try:
        column_index, column = next(
            (i, c)
            for i, c in enumerate(cached_result.table_metadata.columns)
            if c.name == colname
        )
    except StopIteration:
        return JsonResponse({"error": f'column "{colname}" not found'}, status=404)

    if not isinstance(column.type, ColumnType.Text):
        # We only return text values.
        #
        # Rationale: this is only used in Refine and Filter by Value. Both
        # force text. The user can query a column before it's converted to
        # text; but if he/she does, we shouldn't format as text unless we have
        # a viable workflow that needs it. (Better would be to force the user
        # to convert to text before doing anything else, no?)
        return JsonResponse({"values": {}})

    try:
        # raise CorruptCacheError
        with open_cached_render_result(cached_result) as result:
            arrow_table = result.table.table
            chunked_array = arrow_table.column(column_index)
    except CorruptCacheError:
        # We _could_ return an empty result set; but our only goal here is
        # "don't crash" and this 404 seems to be the simplest implementation.
        # (We assume that if the data is deleted, the user has moved elsewhere
        # and this response is going to be ignored.)
        return JsonResponse({"error": f'column "{colname}" not found'}, status=404)

    if chunked_array.num_chunks == 0:
        value_counts = {}
    else:
        assert chunked_array.num_chunks == 1

        # Assume type is text. (We checked column.type is ColumnType.Text above.)
        chunk = chunked_array.chunks[0]
        if not hasattr(chunk, "dictionary"):
            chunk = chunk.dictionary_encode()

        try:
            max_index = max(v.as_py() for v in chunk.indices if v is not pa.NULL)
        except ValueError:
            # all nulls. Hack with "-1" makes the algorithm not-crash.
            max_index = -1

        counts = np.zeros(
            max_index + 1, dtype=int
        )  # if max_index = -1, counts is empty
        for v in chunk.indices:
            if v is not pa.NULL:
                counts[v.as_py()] += 1
        value_counts = {
            value.as_py(): int(count) for value, count in zip(chunk.dictionary, counts)
        }

    return JsonResponse({"values": value_counts})


N_ROWS_PER_TILE = 200
N_COLUMNS_PER_TILE = 50


@api_view(["GET"])
@_with_wf_module_for_read
def wfmodule_tile(
    request: HttpRequest,
    wf_module: WfModule,
    delta_id: int,
    tile_row: int,
    tile_column: int,
):
    if wf_module.last_relevant_delta_id != delta_id:
        return HttpResponseNotFound(
            f"Requested delta {delta_id} but wf_module is "
            f"at delta {wf_module.last_relevant_delta_id}"
        )

    if wf_module.status != "ok":
        return HttpResponseNotFound(
            f'Requested wf_module has status "{wf_module.status}" but '
            'we only render "ok" modules'
        )

    cached_result = wf_module.cached_render_result

    if cached_result is None:
        return HttpResponseNotFound(f"This module has no cached result")

    if cached_result.delta_id != delta_id:
        return HttpResponseNotFound(
            f"Requested delta {delta_id} but cached render result is "
            f"at delta {cached_result.delta_id}"
        )

    # cbegin/cend: column indexes
    cbegin = N_COLUMNS_PER_TILE * tile_column
    cend = N_COLUMNS_PER_TILE * (tile_column + 1)
    rbegin = N_ROWS_PER_TILE * tile_row
    rend = N_ROWS_PER_TILE * (tile_row + 1)

    try:
        data = read_cached_render_result_pydict(
            cached_result,
            only_columns=range(cbegin, cend),
            only_rows=range(rbegin, rend),
        )
        columns = cached_result.table_metadata.columns[cbegin:cend]
        records = _pydict_to_json_records(data, columns, rend - rbegin)
    except CorruptCacheError:
        raise  # TODO handle this case!

    return JsonResponse(records)


class SubprocessOutputFileLike(io.RawIOBase):
    """
    Run a subrocess; .read() reads its stdout and stderr (combined).

    __init__() will only return after the process starts producing output.
    This requirement lets us raise OSError during startup; it also means a
    caller with knowledge of the subprocess's behavior may safely delete a file
    the subprocess is reading from, before the subprocess is finished reading
    it.

    On close(), kill the subprocess (if it's still running) and wait for it.

    close() is the only way to wait for the subprocess. Don't worry: __del__()
    calls close().

    If read() is called after the subprocess terminates and the subprocess's
    exit code is not 0, raise IOError.

    Not thread-safe.
    """

    def __init__(self, args):
        super().__init__()

        # Raises OSError
        self.process = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        # Wait for subprocess to begin outputting data. After that, the caller
        # may delete input files safely, assuming the subprocess already has
        # them open and thus can continue reading from them after they're
        # deleted.
        self._await_stdout_ready()

    def _await_stdout_ready(self):
        """
        Wait until `self.process.stdout.read()` is guaranteed not to block.
        """
        with selectors.DefaultSelector() as selector:
            selector.register(self.process.stdout, selectors.EVENT_READ)
            while len(selector.select()) == 0:
                pass

    def readable(self):
        return True

    def fileno(self):
        return self.process.stdout.fileno()

    def readinto(self, b):
        ret = self.process.stdout.readinto(b)
        return ret

    def close(self):
        if self.closed:
            return

        self.process.stdout.close()
        self.process.kill()
        # wait() should not deadlock, because process will certainly die.
        self.process.wait()  # ignore exit code
        super().close()  # sets self.closed


@api_view(["GET"])
@_with_wf_module_for_read
def wfmodule_public_json(request: HttpRequest, wf_module: WfModule):
    def schedule_render_and_suggest_retry():
        """
        Schedule a render and return a response asking the user to retry.

        It is a *bug* that we publish URLs that aren't guaranteed to work.
        Because we publish URLs that do not work, let's be transparent and
        give them the 500-level error code they deserve.
        """
        # We don't have a cached result, and we don't know how long it'll
        # take to get one. The user will simply need to try again....
        nonlocal wf_module
        workflow = wf_module.workflow
        async_to_sync(rabbitmq.queue_render)(workflow.id, workflow.last_delta_id)
        response = JsonResponse([], safe=False, status=503)
        response["Retry-After"] = "30"
        return response

    cached_result = wf_module.cached_render_result
    if not cached_result:
        return schedule_render_and_suggest_retry()

    try:
        with downloaded_parquet_file(cached_result) as parquet_path:
            output = SubprocessOutputFileLike(
                ["/usr/bin/parquet-to-text-stream", str(parquet_path), "json"]
            )
            # It's okay to delete the file now (i.e., exit the context manager)
    except CorruptCacheError:
        return schedule_render_and_suggest_retry()

    return FileResponse(
        output,
        as_attachment=True,
        filename=(
            "Workflow %d - %s-%d.json"
            % (cached_result.workflow_id, wf_module.module_id_name, wf_module.id)
        ),
        content_type="application/json",
    )


@_with_wf_module_for_read
def wfmodule_public_csv(request: HttpRequest, wf_module: WfModule):
    def schedule_render_and_suggest_retry():
        """
        Schedule a render and return a response asking the user to retry.

        It is a *bug* that we publish URLs that aren't guaranteed to work.
        Because we publish URLs that do not work, let's be transparent and
        give them the 500-level error code they deserve.
        """
        # We don't have a cached result, and we don't know how long it'll
        # take to get one. The user will simply need to try again....
        nonlocal wf_module
        workflow = wf_module.workflow
        async_to_sync(rabbitmq.queue_render)(workflow.id, workflow.last_delta_id)
        response = HttpResponse(b"", content_type="text/csv", status=503)
        response["Retry-After"] = "30"
        return response

    cached_result = wf_module.cached_render_result
    if not cached_result:
        return schedule_render_and_suggest_retry()

    try:
        with downloaded_parquet_file(cached_result) as parquet_path:
            output = SubprocessOutputFileLike(
                ["/usr/bin/parquet-to-text-stream", str(parquet_path), "csv"]
            )
            # It's okay to delete the file now (i.e., exit the context manager)
    except CorruptCacheError:
        return schedule_render_and_suggest_retry()

    return FileResponse(
        output,
        as_attachment=True,
        filename=(
            "Workflow %d - %s-%d.csv"
            % (cached_result.workflow_id, wf_module.module_id_name, wf_module.id)
        ),
        content_type="text/csv; charset=utf-8; header=present",
    )
