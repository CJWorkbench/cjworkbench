from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, HttpResponseNotFound, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from rest_framework import status
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from server.models import Workflow, WfModule
from server.serializers import WfModuleSerializer
from server.execute import execute_wfmodule
from server.versions import bump_workflow_version
import pandas as pd

@api_view(['GET', 'DELETE'])
@renderer_classes((JSONRenderer,))
def wfmodule_detail(request, pk, format=None):
    try:
        wf_module = WfModule.objects.get(pk=pk)
    except WfModule.DoesNotExist:
        return HttpResponseNotFound()

    if not wf_module.user_authorized(request.user):
        return HttpResponseForbidden()

    if request.method == 'GET':
        serializer = WfModuleSerializer(wf_module)
        return Response(serializer.data)

    elif request.method == 'DELETE':
        workflow = wf_module.workflow
        wf_module.delete()
        bump_workflow_version(workflow, notify_client=False) # bump after delete in case delete fails
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@renderer_classes((JSONRenderer,))
def wfmodule_render(request, pk, format=None):
    if request.method == 'GET':
        try:
            wf_module = WfModule.objects.get(pk=pk)
        except WfModule.DoesNotExist:
            return HttpResponseNotFound()

        if not wf_module.user_authorized(request.user):
            return HttpResponseForbidden()

        table = execute_wfmodule(wf_module)
        d = table.reset_index().to_json(orient='records')
        return HttpResponse(d, content_type="application/json")


# /input is just /render on the previous wfmodule
@api_view(['GET'])
@renderer_classes((JSONRenderer,))
def wfmodule_input(request, pk, format=None):
    if request.method == 'GET':
        try:
            wf_module = WfModule.objects.get(pk=pk)
        except WfModule.DoesNotExist:
            return HttpResponseNotFound()

        if not wf_module.user_authorized(request.user):
            return HttpResponseForbidden()

        prev_modules = WfModule.objects.filter(workflow=wf_module.workflow, order__lt=wf_module.order)
        if not prev_modules:
            table = pd.DataFrame()
        else:
            table = execute_wfmodule(prev_modules.last())

        d = table.reset_index().to_json(orient='records')
        return HttpResponse(d, content_type="application/json")


# Public access to wfmodule output. Basically just /render with different auth
@api_view(['GET'])
@renderer_classes((JSONRenderer,))
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