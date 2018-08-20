from datetime import timedelta
import json
import re
from typing import Optional
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, \
        Http404, HttpResponseNotFound, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import dateparse, timezone
from django.views.decorators.clickjacking import xframe_options_exempt
import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype
from rest_framework import status
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from server.models import WfModule, StoredObject
from server.serializers import WfModuleSerializer
from server import execute
from server.models import DeleteModuleCommand, ChangeDataVersionCommand, \
        ChangeWfModuleNotesCommand, ChangeWfModuleUpdateSettingsCommand
from server.utils import units_to_seconds
from server.dispatch import module_get_html_bytes
from server.templatetags.json_filters import escape_potential_hack_chars
from server import websockets


_MaxNRowsPerRequest = 300


def _client_attributes_that_change_on_render(wf_module):
    return {
        'error_msg': wf_module.error_msg,
        'status': wf_module.status,
        # TODO add columns here
    }


def execute_and_notify(wf_module, only_return_headers=False):
    """
    Render (and cache) a WfModule; send websocket updates and return result.
    """
    workflow = wf_module.workflow
    with workflow.cooperative_lock():
        priors = {}
        for a_wf_module in workflow.wf_modules.all():
            priors[a_wf_module.id] = \
                _client_attributes_that_change_on_render(a_wf_module)

        result = execute.execute_wfmodule(
            wf_module,
            only_return_headers=only_return_headers
        )

        changes = {}
        for a_wf_module in workflow.wf_modules.all():
            prior = priors[a_wf_module.id]
            current = _client_attributes_that_change_on_render(a_wf_module)

            if current != prior:
                changes[str(a_wf_module.id)] = current

    if changes:
        websockets.ws_client_send_delta_sync(wf_module.workflow_id, {
            'updateWfModules': changes
        })

    return result


def _lookup_wf_module(pk: int) -> WfModule:
    """Find a Workflow and WfModule based on pk (no access control).

    Raises Http404 if pk is not found in the database.
    """
    wf_module = get_object_or_404(WfModule, pk=pk)

    # Look up workflow now, so we don't look it up later
    wf_module.workflow  # or ObjectDoesNotExist

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
                    wf_module.is_collapsed = request.data['collapsed']
                    wf_module.save()

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
def _make_render_dict(result, startrow=None, endrow=None):
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

    result = execute_and_notify(wf_module)
    j = _make_render_dict(result, startrow, endrow)
    return JsonResponse(j)


_html_head_start_re = re.compile(rb'<\s*head[^>]*>', re.IGNORECASE)


@api_view(['GET'])
@xframe_options_exempt
def wfmodule_output(request, pk, format=None):
    wf_module = _lookup_wf_module_for_read(pk, request)

    html = module_get_html_bytes(wf_module)

    result = execute_and_notify(wf_module)

    # TODO nix params. Use result.json_dict instead.
    params = wf_module.create_parameter_dict(result.dataframe)

    input_dict = _make_render_dict(result)

    init_data = {
        'input': input_dict,
        'params': params,
        'embeddata': result.json,
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

    result = execute_and_notify(wf_module)

    return JsonResponse(result.json)


@api_view(['GET'])
@renderer_classes((JSONRenderer,))
def wfmodule_input_value_counts(request, pk):
    wf_module = _lookup_wf_module_for_read(pk, request)

    with wf_module.workflow.cooperative_lock():
        input_wf_module = _previous_wf_module(wf_module)
        if not input_wf_module:
            return JsonResponse(
                {'error': 'Module has no input'},
                status=404
            )

        try:
            column = wf_module.get_param_column('column')
        except ValueError:
            return JsonResponse(
                {'error': 'Module is missing a "column" parameter'},
                status=404
            )

        if not column:
            # User has not yet chosen a column. Empty response.
            return JsonResponse({'values': {}})

        result = execute_and_notify(input_wf_module)
        table = result.dataframe

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


def _previous_wf_module(wf_module: WfModule) -> Optional[WfModule]:
    """
    Find the WfModule whose output is `wf_module`'s input.

    Return None if there is no previous WfModule.

    Must be called within a `Workflow.cooperative_lock`.
    """
    return wf_module.workflow.wf_modules \
        .filter(order__lt=wf_module.order) \
        .last()


# returns a list of columns and their simplified types
@api_view(['GET'])
@renderer_classes((JSONRenderer,))
def wfmodule_columns(request, pk, format=None):
    wf_module = _lookup_wf_module_for_read(pk, request)

    result = execute_and_notify(wf_module, only_return_headers=True)
    ret_types = [{'name': c, 'type': t}
                 for c, t in zip(result.column_names, result.column_types)]

    return HttpResponse(json.dumps(ret_types), content_type="application/json")


# Public access to wfmodule output. Basically just /render with different auth
# and output format
# NOTE: does not support startrow/endrow at the moment
@api_view(['GET'])
@renderer_classes((JSONRenderer,))
def wfmodule_public_output(request, pk, type, format=None):
    wf_module = _lookup_wf_module_for_read(pk, request)

    result = execute_and_notify(wf_module)

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

    with wf_module.workflow.cooperative_lock():
        stored_objects = wf_module.stored_objects.filter(
            stored_at__in=request.data['versions']
        )

        stored_objects.update(read=True)

    return Response(status=status.HTTP_204_NO_CONTENT)
