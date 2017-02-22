from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import renderer_classes
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from server.models import Module, Workflow, WfModule, ParameterSpec, ParameterVal
from server.serializers import ParameterValSerializer
from server.execute import execute_workflow, execute_wfmodule
from server.dispatch import module_dispatch_event
from server.versions import bump_workflow_version

# ---- Parameter ----

# Get or set parameter value
@api_view(['GET', 'PATCH'])
@renderer_classes((JSONRenderer,))
def parameterval_detail(request, pk, format=None):
    try:
        param = ParameterVal.objects.get(pk=pk)
    except ParameterVal.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = ParameterValSerializer(param)
        return Response(serializer.data)

    elif request.method == 'PATCH':

        # change parameter value
        data = request.data
        if ParameterSpec.STRING in data.keys():
            param.string = data[ParameterSpec.STRING]
        elif ParameterSpec.TEXT in data.keys():
            param.text = data[ParameterSpec.TEXT]
        elif ParameterSpec.NUMBER in data.keys():
            param.number = data[ParameterSpec.NUMBER]
        param.save()

        # TODO this isn't a real error handling framework, only clear the error if we caused it!
        param.wf_module.set_ready(notify=False)

        # increment workflow version number, triggers global re-render
        bump_workflow_version(param.wf_module.workflow)

        return Response(status=status.HTTP_204_NO_CONTENT)


# Handle a parameter event (like someone clicking the fetch button)
# Get or set parameter value
@api_view(['POST'])
@renderer_classes((JSONRenderer,))
def parameterval_event(request, pk, format=None):
    try:
        param = ParameterVal.objects.get(pk=pk)
    except ParameterVal.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    # change parameter value
    data = request.data
    module_dispatch_event(param, data)

    return Response(status=status.HTTP_204_NO_CONTENT)
