from datetime import timedelta
import json
import re
from asgiref.sync import async_to_sync
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, \
        Http404, HttpResponseNotFound, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import dateparse, timezone
from django.views.decorators.clickjacking import xframe_options_exempt
import numpy as np
from rest_framework import status
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from server.models import WfModule, StoredObject
from server.serializers import WfModuleSerializer
from server import execute
from server.models import DeleteModuleCommand, ChangeDataVersionCommand, \
        ChangeWfModuleNotesCommand, ChangeWfModuleUpdateSettingsCommand
from server.modules.types import ProcessResult
import server.utils
from server.utils import units_to_seconds
from server.dispatch import module_get_html_bytes
from server.templatetags.json_filters import escape_potential_hack_chars


_MaxNRowsPerRequest = 300


def _client_attributes_that_change_on_render(wf_module):
    cached_output_columns = wf_module.get_cached_output_columns()
    if cached_output_columns is None:
        output_columns = None
    else:
        output_columns = [{'name': c.name, 'type': c.type}
                          for c in cached_output_columns]

    return {
        'error_msg': wf_module.error_msg,
        'quick_fixes': wf_module.cached_render_result_quick_fixes,
        'status': wf_module.status,
        'output_columns': output_columns,
    }


def _lookup_wf_module(pk: int) -> WfModule:
    """Find a Workflow and WfModule based on pk (no access control).

    Raises Http404 if pk is not found in the database.
    """
    wf_module = get_object_or_404(WfModule, pk=pk)

    # Look up workflow now, so we don't look it up later
    if not wf_module.workflow:
        # We can't read the data in here, because we don't know the workflow so
        # we can't lock it.
        raise Http404()

    return wf_module


def _lookup_wf_module_for_read(pk: int, request: HttpRequest) -> WfModule:
    """Find a WfModule based on pk.

    Raises Http404 if pk is not found in the database, or PermissionDenied if
    the person requesting does not have read access.
    """
    wf_module = _lookup_wf_module(pk)  # or raise Http404

    if not wf_module.workflow.request_authorized_read(request):
        raise PermissionDenied()

    return wf_module


def _lookup_wf_module_for_write(pk: int, request: HttpRequest) -> WfModule:
    """Find a WfModule based on pk.

    Raises Http404 if pk is not found in the database, or PermissionDenied if
    the person requesting does not have write access.
    """
    wf_module = _lookup_wf_module(pk)  # or raise Http404

    if not wf_module.workflow.request_authorized_write(request):
        raise PermissionDenied()

    return wf_module


# The guts of patch commands for various WfModule fields
def patch_notes(wf_module, data):
    async_to_sync(ChangeWfModuleNotesCommand.create)(wf_module, data['notes'])


def patch_update_settings(wf_module, data, request):
    auto_update_data = data['auto_update_data']

    if auto_update_data and (('update_interval' not in data)
                             or ('update_units' not in data)):
        raise ValueError('missing update_interval and update_units fields')

    # Use current time as base update time. Not the best?
    interval = units_to_seconds(int(data['update_interval']),
                                data['update_units'])
    next_update = timezone.now() + timedelta(seconds=interval)
    async_to_sync(ChangeWfModuleUpdateSettingsCommand.create)(
        wf_module,
        auto_update_data,
        next_update,
        interval
    )


# Main /api/wfmodule/xx call. Can do a lot of different things depending on
# request type
@api_view(['GET', 'DELETE', 'PATCH'])
@renderer_classes((JSONRenderer,))
def wfmodule_detail(request, pk, format=None):
    if request.method in ['HEAD', 'GET']:
        wf_module = _lookup_wf_module_for_read(pk, request)
    else:
        wf_module = _lookup_wf_module_for_write(pk, request)

    if request.method == 'GET':
        # No need to execute_and_wait(): out-of-date response is fine
        with wf_module.workflow.cooperative_lock():
            serializer = WfModuleSerializer(wf_module)
            return Response(serializer.data)

    elif request.method == 'DELETE':
        delta = async_to_sync(DeleteModuleCommand.create)(wf_module)
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

            if 'notes' in request.data:
                patch_notes(wf_module, request.data)

            if 'auto_update_data' in request.data:
                patch_update_settings(wf_module, request.data, request)

                if bool(request.data['auto_update_data']):
                    server.utils.log_user_event(
                        request,
                        'Enabled auto-update',
                        {
                            'wfModuleId': wf_module.id
                        }
                    )

            if 'collapsed' in request.data:
                wf_module.is_collapsed = request.data['collapsed']
                wf_module.save(update_fields=['is_collapsed'])

            if 'notifications' in request.data:
                notifications = bool(request.data['notifications'])
                wf_module.notifications = notifications
                wf_module.save(update_fields=['notifications'])

                if notifications:
                    server.utils.log_user_event(
                        request,
                        'Enabled email notifications',
                        {
                            'wfModuleId': wf_module.id
                        }
                    )

        except ValueError as e:  # TODO make this less generic
            return Response({'message': str(e), 'status_code': 400}, status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_204_NO_CONTENT)


# ---- render / input / livedata ----
# These endpoints return actual table data

# Helper method that produces json output for a table + start/end row
# Also silently clips row indices
def _make_render_dict(cached_result, startrow=None, endrow=None):
    if not cached_result:
        result = ProcessResult()
    else:
        result = cached_result.result

    nrows = len(result.dataframe)
    if startrow is None:
        startrow = 0
    if endrow is None:
        endrow = startrow + _MaxNRowsPerRequest

    startrow = max(0, startrow)
    endrow = min(nrows, endrow, startrow + _MaxNRowsPerRequest)

    table = result.dataframe[startrow:endrow]

    # In a sane and just world, we could now just do something like
    #  rows = table.to_dict(orient='records')
    # Alas, this is not the world we live in. Several problems. First,
    #  json.dumps(table.to_dict)
    # does not convert NaN to null. It also fails on int64 columns.

    # The workaround is to usr table.to_json to get a string, then parse it.
    rows = json.loads(table.to_json(orient="records", date_format='iso'))
    return {
        'total_rows': nrows,
        'start_row': startrow,
        'end_row': endrow,
        'columns': result.column_names,
        'rows': rows,
        'column_types': result.column_types,
    }


def int_or_none(x):
    return int(x) if x is not None else None


# /render: return output table of this module
@api_view(['GET'])
@renderer_classes((JSONRenderer,))
def wfmodule_render(request, pk, format=None):
    wf_module = _lookup_wf_module_for_read(pk, request)

    # Get first and last row from query parameters, or default to all if not
    # specified
    try:
        startrow = int_or_none(request.GET.get('startrow'))
        endrow = int_or_none(request.GET.get('endrow'))
    except ValueError:
        return Response({'message': 'bad row number', 'status_code': 400},
                        status=status.HTTP_400_BAD_REQUEST)

    cached_result = execute.execute_and_wait(wf_module.workflow, wf_module)

    j = _make_render_dict(cached_result, startrow, endrow)
    return JsonResponse(j)


_html_head_start_re = re.compile(rb'<\s*head[^>]*>', re.IGNORECASE)


@api_view(['GET'])
@xframe_options_exempt
def wfmodule_output(request, pk, format=None):
    wf_module = _lookup_wf_module_for_read(pk, request)

    html = module_get_html_bytes(wf_module)

    cached_result = execute.execute_and_wait(wf_module.workflow, wf_module)
    result_json = cached_result.json

    init_data = {
        'embeddata': result_json,
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
def wfmodule_embeddata(request, pk):
    wf_module = _lookup_wf_module_for_read(pk, request)

    cached_result = execute.execute_and_wait(wf_module.workflow, wf_module)
    result_json = cached_result.json

    return JsonResponse(result_json)


@api_view(['GET'])
@renderer_classes((JSONRenderer,))
def wfmodule_value_counts(request, pk):
    wf_module = _lookup_wf_module_for_read(pk, request)

    try:
        column = request.GET['column']
    except KeyError:
        return JsonResponse(
            {'error': 'Missing a "column" parameter'},
            status=400
        )

    if not column:
        # User has not yet chosen a column. Empty response.
        return JsonResponse({'values': {}})

    cached_result = execute.execute_and_wait(wf_module.workflow, wf_module)
    table = cached_result.result.dataframe

    try:
        series = table[column]
    except KeyError:
        return JsonResponse({'error': f'column "{column}" not found'},
                            status=404)

    # We only handle string. If it's not string, convert to string.
    if not (series.dtype == object or hasattr(series, 'cat')):
        t = series.astype(str)
        t[series.isna()] = np.nan
        series = t

    value_counts = series.value_counts().to_dict()

    return JsonResponse({'values': value_counts})

N_ROWS_PER_TILE = 200
N_COLUMNS_PER_TILE = 50

@api_view(['GET'])
def wfmodule_tile(request, pk, delta_id, tile_row, tile_column):
    wf_module = _lookup_wf_module_for_read(pk, request)

    if str(wf_module.last_relevant_delta_id) != delta_id:
        return HttpResponseNotFound(
            f'Requested delta {delta_id} but wf_module is '
            f'at delta {wf_module.last_relevant_delta_id}'
        )

    if wf_module.status != 'ok':
        return HttpResponseNotFound(
            f'Requested wf_module has status "{wf_module.status}" but '
            'we only render "ok" modules'
        )

    cached_result = wf_module.get_cached_render_result()

    if not cached_result:
        return HttpResponseNotFound(f'This module has no cached result')

    if str(cached_result.delta_id) != delta_id:
        return HttpResponseNotFound(
            f'Requested delta {delta_id} but cached render result is '
            f'at delta {cached_result.delta_id}'
        )

    # cbegin/cend: column indexes
    cbegin = N_COLUMNS_PER_TILE * int(tile_column)
    cend = N_COLUMNS_PER_TILE * (int(tile_column) + 1)

    # TODO handle races in the following file reads....
    pf = cached_result.parquet_file
    df = pf.to_pandas(columns=cached_result.column_names[cbegin:cend])

    rbegin = N_ROWS_PER_TILE * int(tile_row)
    rend = N_ROWS_PER_TILE * (int(tile_row) + 1)

    df = df.iloc[rbegin:rend]

    json_string = df.to_json(orient='values', date_format='iso')

    return HttpResponse(json_string, content_type='application/json')

# Public access to wfmodule output. Basically just /render with different auth
# and output format
# NOTE: does not support startrow/endrow at the moment
@api_view(['GET'])
@renderer_classes((JSONRenderer,))
def wfmodule_public_output(request, pk, type, format=None):
    wf_module = _lookup_wf_module_for_read(pk, request)

    cached_result = execute.execute_and_wait(wf_module.workflow, wf_module)
    result = cached_result.result

    if type == 'json':
        d = result.dataframe.to_json(orient='records')
        return HttpResponse(d, content_type="application/json")
    elif type == 'csv':
        d = result.dataframe.to_csv(index=False)
        return HttpResponse(d, content_type="text/csv")
    else:
        raise Http404()


# Get list of data versions, or set current data version
@api_view(['GET', 'PATCH'])
@renderer_classes((JSONRenderer,))
def wfmodule_dataversion(request, pk, format=None):
    if request.method == 'GET':
        wf_module = _lookup_wf_module_for_read(pk, request)

        with wf_module.workflow.cooperative_lock():
            versions = wf_module.list_fetched_data_versions()
            current_version = wf_module.get_fetched_data_version()
            response = {'versions': versions, 'selected': current_version}

        return Response(response)

    elif request.method == 'PATCH':
        wf_module = _lookup_wf_module_for_write(pk, request)

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

        async_to_sync(ChangeDataVersionCommand.create)(
            wf_module,
            stored_object.stored_at
        )

        if not stored_object.read:
            stored_object.read = True
            stored_object.save(update_fields=['read'])

        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['PATCH'])
@renderer_classes((JSONRenderer,))
def wfmodule_dataversion_read(request, pk):
    wf_module = _lookup_wf_module_for_write(pk, request)

    with wf_module.workflow.cooperative_lock():
        stored_objects = wf_module.stored_objects.filter(
            stored_at__in=request.data['versions']
        )

        stored_objects.update(read=True)

    return Response(status=status.HTTP_204_NO_CONTENT)
