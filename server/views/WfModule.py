import datetime
import json
import re
from typing import Any, Dict, List
from asgiref.sync import async_to_sync
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import (
    HttpRequest,
    HttpResponse,
    Http404,
    HttpResponseNotFound,
    JsonResponse,
)
from django.shortcuts import get_object_or_404
from django.views.decorators.clickjacking import xframe_options_exempt
import pyarrow
from rest_framework import status
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from cjwstate.rendercache import CorruptCacheError, open_cached_render_result
from cjwstate.models import Tab, WfModule, Workflow
from cjwstate.models.loaded_module import module_get_html_bytes
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


def _arrow_array_to_json_list(array: pyarrow.ChunkedArray) -> List[Any]:
    """
    Convert `array` to a JSON-encodable List.

    Strings become Strings; Numbers become int/float; Datetimes become
    ISO8601-encoded Strings.
    """
    if isinstance(array.type, pyarrow.TimestampType):
        multiplier = 1.0 / TimestampUnits[array.type.unit]
        return [
            datetime.datetime.utcfromtimestamp(v.value * multiplier).isoformat() + "Z"
            for v in array
        ]
    else:
        return array.to_pylist()


def _arrow_table_to_json_records(
    table: pyarrow.Table, begin: int, end: int
) -> List[Dict[str, Any]]:
    """
    Convert `table` to JSON records.

    Slice from `begin` (inclusive, first is 0) to `end` (exclusive).

    String values become Strings; Number values become int/float; Datetime
    values become ISO8601-encoded Strings.
    """
    # Select the values we want -- columnar, so memory accesses are contiguous
    values = {
        column.name: _arrow_array_to_json_list(column[begin:end])
        for column in table.itercolumns()
    }
    # Transpose into JSON records
    return [{k: v[i] for k, v in values.items()} for i in range(end - begin)]


# Helper method that produces json output for a table + start/end row
# Also silently clips row indices
# Now reading a maximum of 101 columns directly from cache parquet
def _make_render_tuple(cached_result, startrow=None, endrow=None):
    """Build (startrow, endrow, json_rows) data."""
    columns = cached_result.table_metadata.columns[
        # Return one row more than configured, so the client knows there
        # are "too many rows".
        : (settings.MAX_COLUMNS_PER_CLIENT_REQUEST + 1)
    ]
    column_names = [c.name for c in columns]

    if startrow is None:
        startrow = 0
    if endrow is None:
        endrow = startrow + _MaxNRowsPerRequest

    # raise CorruptCacheError
    with open_cached_render_result(cached_result, only_columns=column_names) as result:
        startrow = max(0, startrow)
        endrow = min(
            result.table.table.num_rows, endrow, startrow + _MaxNRowsPerRequest
        )
        records = _arrow_table_to_json_records(result.table.table, startrow, endrow)

    return (startrow, endrow, records)


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
            startrow, endrow, records = _make_render_tuple(
                cached_result, startrow, endrow
            )
        except CorruptCacheError:
            # assume we'll get another request after execute finishes
            return JsonResponse({"start_row": 0, "end_row": 0, "rows": []})

        return JsonResponse({"start_row": startrow, "end_row": endrow, "rows": records})


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
        column = next(
            c for c in cached_result.table_metadata.columns if c.name == colname
        )
    except StopIteration:
        return JsonResponse({"error": f'column "{colname}" not found'}, status=404)

    # raise CorruptCacheError
    try:
        with open_cached_render_result(
            cached_result, only_columns=[column.name]
        ) as result:
            series = result.table.table[0].to_pandas()
    except CorruptCacheError:
        # We _could_ return an empty result set; but our only goal here is
        # "don't crash" and this 404 seems to be the simplest implementation.
        # (We assume that if the data is deleted, the user has moved elsewhere
        # and this response is going to be ignored.)
        return JsonResponse({"error": f'column "{colname}" not found'}, status=404)

    # We only handle string. If it's not string, convert to string. (Rationale:
    # this is used in Refine and Filter by Value, which are both solely
    # String-based for now. Excel and Google Sheets only filter by String
    # values, so we're in good company.) Remember: in JavaScript, Object keys
    # must be String.
    series = column.type.format_series(series)
    value_counts = series.value_counts().to_dict()

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

    only_columns = cached_result.column_names[cbegin:cend]
    try:
        with open_cached_render_result(
            cached_result, only_columns=only_columns
        ) as result:
            records = _arrow_table_to_json_records(result.table.table, rbegin, rend)
    except CorruptCacheError:
        raise  # TODO handle this case!

    return JsonResponse(records)


# Public access to wfmodule output. Basically just /render with different auth
# and output format
# NOTE: does not support startrow/endrow at the moment
@api_view(["GET"])
@renderer_classes((JSONRenderer,))
@_with_wf_module_for_read
def wfmodule_public_output(
    request: HttpRequest, wf_module: WfModule, export_type: str, format=None
):
    cached_result = wf_module.cached_render_result
    if cached_result:
        try:
            with open_cached_render_result(cached_result) as result:
                table = result.table.table
        except CorruptCacheError:
            table = pyarrow.Table()
    else:
        # We don't have a cached result, and we don't know how long it'll
        # take to get one.
        workflow = wf_module.workflow
        async_to_sync(rabbitmq.queue_render)(workflow.id, workflow.last_delta_id)
        # The user will simply need to try again....
        table = pyarrow.Table()

    if export_type == "json":
        records = _arrow_table_to_json_records(table, 0, table.num_rows)
        return JsonResponse(records, safe=False)
    elif export_type == "csv":
        df = table.to_pandas()
        d = df.to_csv(index=False)
        return HttpResponse(d, content_type="text/csv")
    else:
        raise RuntimeError("Undefined export_type" + export_type)
