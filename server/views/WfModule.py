from django.http import HttpResponse, HttpResponseNotFound, HttpResponseForbidden
from rest_framework import status
from rest_framework.decorators import api_view, renderer_classes, permission_classes
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from server.models import WfModule
from server.serializers import WfModuleSerializer
from server.execute import execute_wfmodule
from django.utils import timezone
from server.models import DeleteModuleCommand, ChangeDataVersionCommand, ChangeWfModuleNotesCommand, ChangeWfModuleUpdateSettingsCommand
from datetime import timedelta
from server.utils import units_to_seconds
import pandas as pd


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
        if not wf_module.user_authorized(request.user):
            return HttpResponseForbidden()

    if not wf_module.workflow.public and not wf_module.user_authorized(request.user):
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = WfModuleSerializer(wf_module)
        return Response(serializer.data)

    elif request.method == 'DELETE':
        DeleteModuleCommand.create(wf_module)
        return Response(status=status.HTTP_204_NO_CONTENT)

    elif request.method == 'PATCH':
        # For patch, we check which fields are set in data, and process all of them
        try:

            if not set(request.data.keys()).intersection({"notes", "auto_update_data", "collapsed"}):
                raise ValueError('Unknown fields: {}'.format(request.data))

            if 'notes' in request.data:
                patch_notes(wf_module, request.data)

            if 'auto_update_data' in request.data:
                patch_update_settings(wf_module, request.data)

            if 'collapsed' in request.data:
                wf_module.set_is_collapsed(request.data['collapsed'], notify=False)

        except Exception as e:
            return Response({'message': str(e), 'status_code': 400}, status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_204_NO_CONTENT)

# /render: return output table of this module
@api_view(['GET'])
@renderer_classes((JSONRenderer,))
@permission_classes((IsAuthenticatedOrReadOnly, ))
def wfmodule_render(request, pk, format=None):
    if request.method == 'GET':
        try:
            wf_module = WfModule.objects.get(pk=pk)
        except WfModule.DoesNotExist:
            return HttpResponseNotFound()

        if not wf_module.user_authorized(request.user) and not wf_module.workflow.public:
            return HttpResponseForbidden()

        table = execute_wfmodule(wf_module)

        # Get first and last row from query parameters, or default to all if not specified
        nrows = len(table)
        try:
            f = int(request.GET.get('firstrow', 0))
            l = int(request.GET.get('lastrow', nrows-1))
        except ValueError:
            return Response({'message': 'bad row number', 'status_code': 400}, status=status.HTTP_400_BAD_REQUEST)

        f = max(0, f)
        l += 1  # so that lastrow is inclusive
        l = min(nrows, l)
        table = table[f:l]

        d = table.to_json(orient='records')
        return HttpResponse(d, content_type="application/json")


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

        if not wf_module.workflow.public and not wf_module.user_authorized(request.user):
            return HttpResponseForbidden()

        prev_modules = WfModule.objects.filter(workflow=wf_module.workflow, order__lt=wf_module.order)
        if not prev_modules:
            table = pd.DataFrame()
        else:
            table = execute_wfmodule(prev_modules.last())

        d = table.to_json(orient='records')
        return HttpResponse(d, content_type="application/json")


# Public access to wfmodule output. Basically just /render with different auth
@api_view(['GET'])
@renderer_classes((JSONRenderer,))
@permission_classes((IsAuthenticatedOrReadOnly, ))
def wfmodule_public_output(request, pk, type, format=None):
    try:
        wf_module = WfModule.objects.get(pk=pk)
    except WfModule.DoesNotExist:
        return HttpResponseNotFound()

    if not wf_module.public_authorized():
        return HttpResponseForbidden()

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
        if not wf_module.workflow.public and not wf_module.user_authorized(request.user):
            return HttpResponseForbidden()
        versions = wf_module.list_stored_data_versions()
        current_version = wf_module.get_stored_data_version()
        response = {'versions': versions, 'selected': current_version}
        return Response(response)

    elif request.method == 'PATCH':
        if not wf_module.user_authorized(request.user):
            return HttpResponseForbidden()

        ChangeDataVersionCommand.create(wf_module, request.data['selected'])
        return Response(status=status.HTTP_204_NO_CONTENT)
