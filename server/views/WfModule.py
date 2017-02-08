from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from server.models import Workflow, WfModule
from server.serializers import WfModuleSerializer
from server.execute import execute_wfmodule
import pandas as pd


@api_view(['GET'])
@renderer_classes((JSONRenderer,))
def wfmodule_detail(request, pk, format=None):
    if request.method == 'GET':
        try:
            wfmodule = WfModule.objects.get(pk=pk)
        except WfModule.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = WfModuleSerializer(wfmodule)
        return Response(serializer.data)


@api_view(['GET'])
@renderer_classes((JSONRenderer,))
def wfmodule_render(request, pk, format=None):
    if request.method == 'GET':
        try:
            wfmodule = WfModule.objects.get(pk=pk)
        except WfModule.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        table = execute_wfmodule(wfmodule)
        d = table.reset_index().to_json(orient='records')
        return HttpResponse(d, content_type="application/json")


# /input is just /render on the previous wfmodule
@api_view(['GET'])
@renderer_classes((JSONRenderer,))
def wfmodule_input(request, pk, format=None):
    if request.method == 'GET':
        try:
            wfmodule = WfModule.objects.get(pk=pk)
        except WfModule.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        prev_modules = WfModule.objects.filter(workflow=wfmodule.workflow, order__lt=wfmodule.order)
        if not prev_modules:
            table = pd.DataFrame()
        else:
            table = execute_wfmodule(prev_modules.last())

        d = table.reset_index().to_json(orient='records')
        return HttpResponse(d, content_type="application/json")