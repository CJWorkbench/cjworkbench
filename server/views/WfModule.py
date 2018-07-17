from django.http import HttpRequest, HttpResponse, HttpResponseNotFound, \
        HttpResponseForbidden, HttpResponseBadRequest, JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from django.utils import dateparse, timezone
from server.models import Workflow, WfModule, StoredObject
from server.serializers import WfModuleSerializer
from server.execute import execute_wfmodule
from server.models import DeleteModuleCommand, ChangeDataVersionCommand, \
        ChangeWfModuleNotesCommand, ChangeWfModuleUpdateSettingsCommand
from datetime import timedelta
from server.utils import units_to_seconds
from server.dispatch import module_get_html_bytes
from server.templatetags.json_filters import escape_potential_hack_chars
import json
import re
import pandas as pd
from django.views.decorators.clickjacking import xframe_options_exempt
from typing import Union

_LookupResponse = Union[HttpResponse, WfModule]


def _lookup_wf_module_no_access_control(pk: int) -> _LookupResponse:
    """Find a Workflow and WfModule based on pk (no access control).

    Returns HttpResponseNotFound if pk is not in the database.
    """
    try:
        wf_module = WfModule.objects.get(pk=pk)
    except WfModule.DoesNotExist:
        return HttpResponseNotFound()

    try:
        # Look up workflow now, so we don't look it up later
        wf_module.workflow
    except Workflow.DoesNotExist:  # race
        return HttpResponseNotFound()

    return wf_module


def _lookup_wf_module_for_read(
        pk: int, request: HttpRequest) -> _LookupResponse:
    """Find a WfModule based on pk.

    Returns HttpResponseNotFound if pk is not in the database, or
    HttpResponseForbidden if the person requesting does not have access.
    """
    wf_module = _lookup_wf_module_no_access_control(pk)
    if isinstance(wf_module, HttpResponse):
        return wf_module

    if not wf_module.workflow.request_authorized_read(request):
        return HttpResponseForbidden()

    return wf_module


def _lookup_wf_module_for_write(
        pk: int, request: HttpRequest) -> _LookupResponse:
    """Find a WfModule based on pk.

    Returns HttpResponseNotFound if pk is not in the database, or
    HttpResponseForbidden if the person requesting does not have access.
    """
    wf_module = _lookup_wf_module_no_access_control(pk)
    if isinstance(wf_module, HttpResponse):
        return wf_module

    if not wf_module.workflow.request_authorized_write(request):
        return HttpResponseForbidden()

    return wf_module


# The guts of patch commands for various WfModule fields
def patch_notes(wf_module, data):
    ChangeWfModuleNotesCommand.create(wf_module, data['notes'])


def patch_update_settings(wf_module, data):
    auto_update_data = data['auto_update_data']

    if auto_update_data and (('update_interval' not in data)
                             or ('update_units' not in data)):
        raise ValueError('missing update_interval and update_units fields')

    # Use current time as base update time. Not the best?
    interval = units_to_seconds(int(data['update_interval']),
                                data['update_units'])
    next_update = timezone.now() + timedelta(seconds=interval)
    ChangeWfModuleUpdateSettingsCommand.create(wf_module, auto_update_data,
                                               next_update, interval)


def get_simple_column_types(table):
    # Get simplified column types of a table
    # and return as a list in the order of the columns
    raw_dtypes = list(table.dtypes)
    ret_types = []
    for dt in raw_dtypes:
        # We are simplifying the data types here.
        # More stuff can be added to these lists if we run into anything new.
        stype = "String"
        if dt in ['int64', 'float64', 'bool']:
            stype = "Number"
        elif dt in ['datetime64[ns]']:
            stype = "Date"
        ret_types.append(stype)
    return ret_types


# Main /api/wfmodule/xx call. Can do a lot of different things depending on
# request type
@api_view(['GET', 'DELETE', 'PATCH'])
@renderer_classes((JSONRenderer,))
def wfmodule_detail(request, pk, format=None):
    if request.method in ['HEAD', 'GET']:
        wf_module = _lookup_wf_module_for_read(pk, request)
    else:
        wf_module = _lookup_wf_module_for_write(pk, request)

    if isinstance(wf_module, HttpResponse):
        return wf_module

    if request.method == 'GET':
        with wf_module.workflow.cooperative_lock():
            serializer = WfModuleSerializer(wf_module)
            return Response(serializer.data)

    elif request.method == 'DELETE':
        delta = DeleteModuleCommand.create(wf_module)
        if delta:
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            # missing wf_module; can happen if two DELETE requests race.
            return HttpResponseNotFound()

    elif request.method == 'PATCH':
        # For patch, we check which fields are set in data, and process all of
        # them
        # TODO: replace all of these with the generic patch method, most of
        # this is unnecessary
        try:
            if not set(request.data.keys()).intersection({"notes", "auto_update_data", "collapsed", "notifications"}):
                raise ValueError('Unknown fields: {}'.format(request.data))

            with wf_module.workflow.cooperative_lock():
                if 'notes' in request.data:
                    patch_notes(wf_module, request.data)

                if 'auto_update_data' in request.data:
                    patch_update_settings(wf_module, request.data)

                if 'collapsed' in request.data:
                    wf_module.set_is_collapsed(request.data['collapsed'], notify=False)

                if 'notifications' in request.data:
                    wf_module.notifications = bool(request.data['notifications'])
                    wf_module.save()

        except Exception as e:
            return Response({'message': str(e), 'status_code': 400}, status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_204_NO_CONTENT)

# ---- render / input / livedata ----
# These endpoints return actual table data

# Helper method that produces json output for a table + start/end row
# Also silently clips row indices
def _make_render_dict(table, startrow=None, endrow=None):
    nrows = len(table)
    if startrow is None:
        startrow = 0
    if endrow is None:
        endrow = nrows

    startrow = max(0, startrow)
    endrow = min(nrows, endrow)
    table = table[startrow:endrow]

    # In a sane and just world, we could now just do something like
    #  rows = table.to_dict(orient='records')
    # Alas, this is not the world we live in. Several problems. First,
    #  json.dumps(table.to_dict)
    # does not convert NaN to null. It also fails on int64 columns.

    # The workaround is to usr table.to_json to get a string, then parse it.
    rows = json.loads(table.to_json(orient="records", date_format='iso'))
    columns = table.columns.values.tolist()
    column_types = get_simple_column_types(table)
    return {
        'total_rows': nrows,
        'start_row': startrow,
        'end_row': endrow,
        'columns': columns,
        'rows': rows,
        'column_types': column_types,
    }


def int_or_none(x):
    return int(x) if x is not None else None


# Shared code between /render and /input
def table_json_response(request, wf_module):
    # Get first and last row from query parameters, or default to all if not
    # specified
    try:
        startrow = int_or_none(request.GET.get('startrow'))
        endrow = int_or_none(request.GET.get('endrow'))
    except ValueError:
        return Response({'message': 'bad row number', 'status_code': 400},
                        status=status.HTTP_400_BAD_REQUEST)

    result = execute_wfmodule(wf_module)
    j = _make_render_dict(result.dataframe, startrow, endrow)
    return JsonResponse(j)


# /render: return output table of this module
@api_view(['GET'])
@renderer_classes((JSONRenderer,))
def wfmodule_render(request, pk, format=None):
    wf_module = _lookup_wf_module_for_read(pk, request)
    if isinstance(wf_module, HttpResponse):
        return wf_module

    with wf_module.workflow.cooperative_lock():
        return table_json_response(request, wf_module)


_html_head_start_re = re.compile(rb'<\s*head[^>]*>', re.IGNORECASE)


@api_view(['GET'])
@xframe_options_exempt
def wfmodule_output(request, pk, format=None):
    wf_module = _lookup_wf_module_for_read(pk, request)
    if isinstance(wf_module, HttpResponse):
        return wf_module

    html = module_get_html_bytes(wf_module)

    result = execute_wfmodule(wf_module)

    # TODO nix params. Use result.json_dict instead.
    params = wf_module.create_parameter_dict(result.dataframe)

    input_dict = _make_render_dict(result.dataframe)

    init_data = {
        'input': input_dict,
        'params': params,
    }
    init_data_bytes = escape_potential_hack_chars(json.dumps(init_data)) \
        .encode('utf-8')

    script_bytes = b''.join([
        b'<script>window.workbench=', init_data_bytes, b'</script>'
    ])

    html_with_js = _html_head_start_re.sub(
        lambda m: m.group(0) + script_bytes,
        html,
        count=1  # so a '<head>' in comments and code won't be replaced
    )

    return HttpResponse(content=html_with_js)


@api_view(['GET'])
@renderer_classes((JSONRenderer,))
def wfmodule_histogram(request, pk, col, format=None):
    wf_module = _lookup_wf_module_for_read(pk, request)
    if isinstance(wf_module, HttpResponse):
        return wf_module

    INTERNAL_COUNT_COLNAME = '__internal_count_column__'

    prev_modules = WfModule.objects.filter(workflow=wf_module.workflow,
                                           order__lt=wf_module.order)
    if not prev_modules:
        return JsonResponse(_make_render_dict(pd.DataFrame()))

    result = execute_wfmodule(prev_modules.last())
    if col not in result.dataframe.columns:
        return JsonResponse({
            'message': 'Column does not exist in module input',
            'status_code': 400
        }, status=status.HTTP_400_BAD_REQUEST)

    hist_table = result.dataframe.groupby(col).size().reset_index()
    hist_table.columns = [col, INTERNAL_COUNT_COLNAME]
    hist_table = hist_table.sort_values(by=[INTERNAL_COUNT_COLNAME, col],
                                        ascending=[False, True])
    hist_table[col] = hist_table[col].astype(str)

    return JsonResponse(_make_render_dict(hist_table))


# /input is just /render on the previous wfmodule
@api_view(['GET'])
@renderer_classes((JSONRenderer,))
def wfmodule_input(request, pk, format=None):
    wf_module = _lookup_wf_module_for_read(pk, request)
    if isinstance(wf_module, HttpResponse):
        return wf_module

    with wf_module.workflow.cooperative_lock():
        # return empty table if this is the first module in the stack
        prev_modules = WfModule.objects.filter(workflow=wf_module.workflow,
                                               order__lt=wf_module.order)
        if not prev_modules:
            return JsonResponse(_make_render_dict(pd.DataFrame()))
        else:
            return table_json_response(request, prev_modules.last())


# returns a list of columns and their simplified types
@api_view(['GET'])
@renderer_classes((JSONRenderer,))
def wfmodule_columns(request, pk, format=None):
    wf_module = _lookup_wf_module_for_read(pk, request)
    if isinstance(wf_module, HttpResponse):
        return wf_module

    with wf_module.workflow.cooperative_lock():
        result = execute_wfmodule(wf_module)
        dtypes = result.dataframe.dtypes.to_dict()

    ret_types = []
    for col in dtypes:
        # We are simplifying the data types here.
        # More stuff can be added to these lists if we run into anything new.
        stype = "String"
        if str(dtypes[col]) in ['int64', 'float64', 'bool']:
            stype = "Number"
        elif str(dtypes[col]) in ['datetime64[ns]']:
            ret_types.append((col, "Date"))
            stype = "Date"
        ret_types.append({
            "name": col,
            "type": stype
        })
    return HttpResponse(json.dumps(ret_types), content_type="application/json")


# Public access to wfmodule output. Basically just /render with different auth
# and output format
# NOTE: does not support startrow/endrow at the moment
@api_view(['GET'])
@renderer_classes((JSONRenderer,))
def wfmodule_public_output(request, pk, type, format=None):
    wf_module = _lookup_wf_module_for_read(pk, request)
    if isinstance(wf_module, HttpResponse):
        return wf_module

    with wf_module.workflow.cooperative_lock():
        table = execute_wfmodule(wf_module)
        if type=='json':
            d = table.to_json(orient='records')
            return HttpResponse(d, content_type="application/json")
        elif type=='csv':
            d = table.to_csv(index=False)
            return HttpResponse(d, content_type="text/csv")
        else:
            return HttpResponseNotFound()


# Get list of data versions, or set current data version
@api_view(['GET', 'PATCH'])
@renderer_classes((JSONRenderer,))
def wfmodule_dataversion(request, pk, format=None):
    if request.method == 'GET':
        wf_module = _lookup_wf_module_for_read(pk, request)
        if isinstance(wf_module, HttpResponse): return wf_module

        with wf_module.workflow.cooperative_lock():
            versions = wf_module.list_fetched_data_versions()
            current_version = wf_module.get_fetched_data_version()
            response = {'versions': versions, 'selected': current_version}

        return Response(response)

    elif request.method == 'PATCH':
        wf_module = _lookup_wf_module_for_write(pk, request)
        if isinstance(wf_module, HttpResponse): return wf_module

        with wf_module.workflow.cooperative_lock():
            date_s = request.data.get('selected', '')
            date = dateparse.parse_datetime(date_s)

            if not date:
                return HttpResponseBadRequest(f'"selected" parameter must be an ISO8601 date; got "{date_s}"')

            try:
                # TODO maybe let's not use microsecond-precision numbers as
                # StoredObject IDs and then send the client
                # millisecond-precision identifiers. We _could_ just pass
                # clients the IDs, for instance.
                #
                # Select a version within 1ms of the (rounded _or_ truncated)
                # version we sent the client.
                #
                # (Let's not change the way we JSON-format dates just to avoid
                # this hack. That would be even worse.)
                stored_object = wf_module.stored_objects.get(
                    stored_at__gte=date - timedelta(microseconds=500),
                    stored_at__lt=date + timedelta(milliseconds=1)
                )
            except StoredObject.DoesNotExist:
                return HttpResponseNotFound(f'No StoredObject with stored_at={date_s}')

            ChangeDataVersionCommand.create(wf_module, stored_object.stored_at)

            if not stored_object.read:
                stored_object.read = True
                stored_object.save()

        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['PATCH'])
@renderer_classes((JSONRenderer,))
def wfmodule_dataversion_read(request, pk):
    wf_module = _lookup_wf_module_for_write(pk, request)
    if isinstance(wf_module, HttpResponse): return wf_module

    with wf_module.workflow.cooperative_lock():
        stored_objects = StoredObject.objects.filter(wf_module=wf_module, \
            stored_at__in=request.data['versions'])

        stored_objects.update(read=True)

    return Response(status=status.HTTP_204_NO_CONTENT)
