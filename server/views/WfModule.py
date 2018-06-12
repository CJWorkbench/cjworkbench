from django.http import HttpResponse, HttpResponseNotFound, HttpResponseForbidden
from rest_framework import status
from rest_framework.decorators import api_view, renderer_classes, permission_classes
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django.utils import timezone
from django.shortcuts import get_object_or_404
from server.models import WfModule, StoredObject
from server.serializers import WfModuleSerializer
from server.execute import execute_wfmodule
from server.models import DeleteModuleCommand, ChangeDataVersionCommand, ChangeWfModuleNotesCommand, ChangeWfModuleUpdateSettingsCommand
from server.dispatch import module_dispatch_output
from datetime import timedelta
from server.utils import units_to_seconds
import json, datetime, pytz, re
import pandas as pd
from django.views.decorators.clickjacking import xframe_options_exempt


# The guts of patch commands for various WfModule fields
def patch_notes(wf_module, data):
    ChangeWfModuleNotesCommand.create(wf_module, data['notes'])


def patch_update_settings(wf_module, data):
    auto_update_data = data['auto_update_data']

    if auto_update_data and (('update_interval' not in data) or ('update_units' not in data)):
        raise ValueError('missing update_interval and update_units fields')

    # Use current time as base update time. Not the best?
    interval = units_to_seconds(int(data['update_interval']), data['update_units'])
    next_update = timezone.now() + timedelta(seconds=interval)
    ChangeWfModuleUpdateSettingsCommand.create(wf_module, auto_update_data, next_update, interval)


def patch_wfmodule(wf_module, data):
    # Just patch it using the built-in Django Rest Framework methods.
    with wf_module.workflow.cooperative_lock():
        serializer = WfModuleSerializer(wf_module, data, partial=True)
        if serializer.is_valid():
            serializer.save()


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


# Main /api/wfmodule/xx call. Can do a lot of different things depending on request type
@api_view(['GET', 'DELETE', 'PATCH'])
@renderer_classes((JSONRenderer,))
@permission_classes((IsAuthenticatedOrReadOnly, ))
def wfmodule_detail(request, pk, format=None):
    try:
        wf_module = WfModule.objects.get(pk=pk)
    except WfModule.DoesNotExist:
        return HttpResponseNotFound()

    if request.method in ['POST', 'DELETE', 'PATCH']:
        if not wf_module.user_authorized_write(request.user):
            return HttpResponseForbidden()

    if not wf_module.user_authorized_read(request.user):
        return HttpResponseNotFound()

    if request.method == 'GET':
        with wf_module.workflow.cooperative_lock():
            serializer = WfModuleSerializer(wf_module)
            return Response(serializer.data)

    elif request.method == 'DELETE':
        delta = DeleteModuleCommand.create(wf_module)
        if delta:
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return HttpResponseNotFound()  # missing wf_module; can happen if two DELETE requests race.

    elif request.method == 'PATCH':
        # For patch, we check which fields are set in data, and process all of them
        # TODO: replace all of these with the generic patch method, most of this is unnecessary
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
                    patch_wfmodule(wf_module, request.data)

        except Exception as e:
            return Response({'message': str(e), 'status_code': 400}, status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_204_NO_CONTENT)

# ---- render / input / livedata ----
# These endpoints return actual table data

# Helper method that produces json output for a table + start/end row
# Also silently clips row indices
def make_render_json(table, startrow=None, endrow=None):
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
    # And in Pandas < 0.22 there is a terrible, terrible bug
    # https://github.com/pandas-dev/pandas/issues/13258#issuecomment-326671257

    # The workaround is to usr table.to_json to get a string, and then glue the other
    # fields we want around that string. Like savages.

    rowstr = table.to_json(orient="records", date_format='iso')
    colnames = table.columns.values.tolist()
    colstr = json.dumps(colnames, ensure_ascii=False)
    typesstr = json.dumps(get_simple_column_types(table))
    outfmt = '{"total_rows": %d, "start_row" :%d, "end_row": %d, "columns": %s, "rows": %s, "column_types": %s}'
    outstr = outfmt % (nrows, startrow, endrow, colstr, rowstr, typesstr)

    return outstr

def int_or_none(x):
    return int(x) if x is not None else None

# Shared code between /render and /input
def table_result(request, wf_module):
    # Get first and last row from query parameters, or default to all if not specified
    try:
        startrow = int_or_none(request.GET.get('startrow'))
        endrow = int_or_none(request.GET.get('endrow'))
    except ValueError:
        return Response({'message': 'bad row number', 'status_code': 400}, status=status.HTTP_400_BAD_REQUEST)

    with wf_module.workflow.cooperative_lock():
        table = execute_wfmodule(wf_module)
        j = make_render_json(table, startrow, endrow)
    return HttpResponse(j, content_type="application/json")


# /render: return output table of this module
@api_view(['GET'])
@renderer_classes((JSONRenderer,))
@permission_classes((IsAuthenticatedOrReadOnly, ))
def wfmodule_render(request, pk, format=None):
    if request.method == 'GET':
        wf_module = get_object_or_404(WfModule, pk=pk)

        # A clutch fix for deleting a module from within itself
        # triggering a 500 error because wf_module.workflow is None
        if not wf_module.workflow:
            empty_table_json = make_render_json(pd.DataFrame(), 0, 0)
            return HttpResponse(empty_table_json, content_type="application/json")

        if not wf_module.workflow.user_authorized_read(request.user):
            return HttpResponseForbidden()

        return table_result(request, wf_module)

@xframe_options_exempt
def wfmodule_output(request, pk, format=None):
    if request.method == 'GET':
        try:
            wf_module = WfModule.objects.get(pk=pk)
        except WfModule.DoesNotExist:
            return HttpResponseNotFound()

        if not wf_module.workflow.user_authorized_read(request.user):
            return HttpResponseForbidden()

        table = execute_wfmodule(wf_module)

        html, input_data, params = module_dispatch_output(wf_module, table, request=request)

        input_data_json = make_render_json(input_data)

        init_data =  json.dumps({
            'input': json.loads(input_data_json),
            'params': params
        })

        js="""
        <script>
        var workbench = %s
        </script>""" % init_data

        head_tag_pattern = re.compile('<\w*[H|h][E|e][A|a][D|d]\w*>')
        result = head_tag_pattern.search(html)

        modified_html = '%s %s %s' % (
            html[:result.end()],
            js,
            html[result.end():]
        )

        return HttpResponse(content=modified_html)


@api_view(['GET'])
@renderer_classes((JSONRenderer,))
@permission_classes((IsAuthenticatedOrReadOnly, ))
def wfmodule_histogram(request, pk, col, format=None):
    if request.method == 'GET':
        try:
            wf_module = WfModule.objects.get(pk=pk)
        except WfModule.DoesNotExist:
            return HttpResponseNotFound()

        if not wf_module.workflow.user_authorized_read(request.user):
            return HttpResponseForbidden()

        INTERNAL_COUNT_COLNAME = '__internal_count_column__'

        prev_modules = WfModule.objects.filter(workflow=wf_module.workflow, order__lt=wf_module.order)
        if not prev_modules:
            return HttpResponse(make_render_json(pd.DataFrame()), content_type="application/json")
        table = execute_wfmodule(prev_modules.last())
        if col not in table.columns:
            return Response({'message': 'Column does not exist in module input', 'status_code': 400}, status=status.HTTP_400_BAD_REQUEST)
        hist_table = table.groupby(col).size().reset_index()
        hist_table.columns = [col, INTERNAL_COUNT_COLNAME]
        hist_table = hist_table.sort_values(by=[INTERNAL_COUNT_COLNAME, col], ascending=[False, True])
        hist_table[col] = hist_table[col].astype(str)

        return HttpResponse(make_render_json(hist_table), content_type="application/json")


# /input is just /render on the previous wfmodule
@api_view(['GET'])
@renderer_classes((JSONRenderer,))
@permission_classes((IsAuthenticatedOrReadOnly, ))
def wfmodule_input(request, pk, format=None):
    if request.method == 'GET':
        try:
            wf_module = WfModule.objects.get(pk=pk)
        except WfModule.DoesNotExist:
            return HttpResponseNotFound()

        if not wf_module.user_authorized_read(request.user):
            return HttpResponseForbidden()

        with wf_module.workflow.cooperative_lock():
            # return empty table if this is the first module in the stack
            prev_modules = WfModule.objects.filter(workflow=wf_module.workflow, order__lt=wf_module.order)
            if not prev_modules:
                return HttpResponse(make_render_json(pd.DataFrame()), content_type="application/json")
            else:
                return table_result(request, prev_modules.last())


# returns a list of columns and their simplified types
@api_view(['GET'])
@renderer_classes((JSONRenderer,))
@permission_classes((IsAuthenticatedOrReadOnly, ))
def wfmodule_columns(request, pk, format=None):
    if request.method == 'GET':
        try:
            wf_module = WfModule.objects.get(pk=pk)
        except WfModule.DoesNotExist:
            return HttpResponseNotFound()

        if not wf_module.workflow.user_authorized_read(request.user):
            return HttpResponseForbidden()

        with wf_module.workflow.cooperative_lock():
            table = execute_wfmodule(wf_module)
            dtypes = table.dtypes.to_dict()

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


# Public access to wfmodule output. Basically just /render with different auth and output format
# NOTE: does not support startrow/endrow at the moment
@api_view(['GET'])
@renderer_classes((JSONRenderer,))
@permission_classes((IsAuthenticatedOrReadOnly, ))
def wfmodule_public_output(request, pk, type, format=None):
    try:
        wf_module = WfModule.objects.get(pk=pk)
    except WfModule.DoesNotExist:
        return HttpResponseNotFound()

    if not wf_module.user_authorized_read(request.user):
        return HttpResponseNotFound()

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
@permission_classes((IsAuthenticatedOrReadOnly, ))
def wfmodule_dataversion(request, pk, format=None):
    try:
        wf_module = WfModule.objects.get(pk=pk)
    except WfModule.DoesNotExist:
        return HttpResponseNotFound()

    if request.method == 'GET':
        if not wf_module.user_authorized_read(request.user):
            return HttpResponseNotFound()

        with wf_module.workflow.cooperative_lock():
            versions = wf_module.list_fetched_data_versions()
            current_version = wf_module.get_fetched_data_version()
            response = {'versions': versions, 'selected': current_version}
            return Response(response)

    elif request.method == 'PATCH':
        if not wf_module.user_authorized_write(request.user):
            return HttpResponseForbidden()

        with wf_module.workflow.cooperative_lock():
            ChangeDataVersionCommand.create(wf_module, datetime.datetime.strptime(request.data['selected'], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=pytz.UTC))

            stored_object_at_version = StoredObject.objects.filter(wf_module=wf_module).get(stored_at=request.data['selected'])

            if not stored_object_at_version.read:
                stored_object_at_version.read = True
                stored_object_at_version.save()

            return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['PATCH'])
@renderer_classes((JSONRenderer,))
def wfmodule_dataversion_read(request, pk):
    try:
        wf_module = WfModule.objects.get(pk=pk)
    except WfModule.DoesNotExist:
        return HttpResponseNotFound()

    if not wf_module.user_authorized_write(request.user):
        return HttpResponseForbidden()

    with wf_module.workflow.cooperative_lock():
        stored_objects = StoredObject.objects.filter(wf_module=wf_module, \
            stored_at__in=request.data['versions'])

        stored_objects.update(read=True)

    return Response(status=status.HTTP_204_NO_CONTENT)
