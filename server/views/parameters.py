from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden, HttpResponseNotFound, HttpResponseBadRequest
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import renderer_classes
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from server.models import Module, Workflow, WfModule, ParameterSpec, ParameterVal
from server.serializers import ParameterValSerializer
from server.execute import execute_wfmodule
from server.dispatch import module_dispatch_event
from server.models import ChangeParameterCommand
import base64

# ---- Parameter ----

# Get or set parameter value
@api_view(['GET', 'PATCH'])
@renderer_classes((JSONRenderer,))
def parameterval_detail(request, pk, format=None):
    try:
        param = ParameterVal.objects.get(pk=pk)
    except ParameterVal.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if not param.user_authorized(request.user):
        return HttpResponseForbidden()

    if request.method == 'GET':
        serializer = ParameterValSerializer(param)
        return Response(serializer.data)

    elif request.method == 'PATCH':
        ChangeParameterCommand.create(param, request.data['value'])
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

    if not param.user_authorized(request.user):
        return HttpResponseForbidden()

    # change parameter value
    data = request.data
    module_dispatch_event(param.wf_module, param, data)

    return Response(status=status.HTTP_204_NO_CONTENT)


# Return a parameter val that is actually an image
@require_GET
def parameterval_png(request, pk):
    try:
        param = ParameterVal.objects.get(pk=pk)
    except ParameterVal.DoesNotExist:
        return HttpResponseNotFound()

    if not param.wf_module.public_authorized():
        return HttpResponseForbidden()

    # is this actually in image? totes hardcoded for now
    if param.parameter_spec.id_name != 'chart':
        return HttpResponseBadRequest()

    # decode the base64 payload of the data URI into a png
    image_data = param.value.partition('base64,')[2]
    binary = base64.b64decode(image_data)
    return HttpResponse(binary, content_type='image/png')
