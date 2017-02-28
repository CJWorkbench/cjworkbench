from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from django.template.response import TemplateResponse
from django.contrib.auth.decorators import login_required
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import renderer_classes
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from server.models import Module, Workflow, WfModule, ParameterSpec, ParameterVal
from server.serializers import WorkflowSerializer
from server.execute import execute_workflow, execute_wfmodule


# ---- Workflows list page ----
@login_required
def workflows2(request):
    return TemplateResponse(request, 'workflows.html', {})

# ---- Workflow ----


# List all workflows, or create a new workflow.
@api_view(['GET', 'POST'])
@renderer_classes((JSONRenderer,))
def workflow_list(request, format=None):
    if request.method == 'GET':
        workflows = Workflow.objects.filter(owner=request.user)
        serializer = WorkflowSerializer(workflows, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = WorkflowSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(owner=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Retrieve, update or delete a workflow instance.
@api_view(['GET', 'PATCH', 'DELETE'])
@renderer_classes((JSONRenderer,))
def workflow_detail(request, pk, format=None):
    try:
        workflow = Workflow.objects.get(pk=pk)
    except Workflow.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if not workflow.user_authorized(request.user):
        return HttpResponseForbidden()

    if request.method == 'GET':
        serializer = WorkflowSerializer(workflow)
        return Response(serializer.data)

    # We use PATCH to set the order of the modules when the user drags.
    elif request.method == 'PATCH':
        for record in request.data:
            wfm = workflow.wf_modules.get(pk=record['id'])
            wfm.order = record['order']
            wfm.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    elif request.method == 'DELETE':
        workflow.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Invoked when user pressess add_module button
@api_view(['PUT'])
@renderer_classes((JSONRenderer,))
def workflow_addmodule(request, pk, format=None):
    try:
        workflow = Workflow.objects.get(pk=pk)
    except Workflow.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if not workflow.user_authorized(request.user):
        return HttpResponseForbidden()

    try:
        moduleID = request.data['moduleID']
        insertBefore = int(request.data['insertBefore'])
        module = Module.objects.get(pk=moduleID)
    except Module.DoesNotExist:
        return Response(status=status.HTTP_400_BAD_REQUEST)

    # create new WfModule, and increment order of every module below this in the workflow
    for wfm in WfModule.objects.filter(workflow=workflow):
        if wfm.order >= insertBefore:
            wfm.order += 1
            wfm.save()
    newwfm = WfModule.objects.create(workflow=workflow, module=module, order=insertBefore)
    newwfm.create_default_parameters()

    return Response(status=status.HTTP_204_NO_CONTENT)

