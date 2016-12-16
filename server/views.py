from django.shortcuts import render
from django.http import HttpResponse

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import renderer_classes
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from server.models import Module
from server.models import Workflow
from server.models import WfModule
from server.serializers import ModuleSerializer
from server.serializers import WorkflowSerializer
from server.serializers import WfModuleSerializer
from server.initmodules import init_modules


def index(request):
    return HttpResponse("Hello, world. You're at the workflow index. <a href=\"/admin\">Admin</a>")

def workflow(request, workflow_id):
    return HttpResponse("You're looking at workflow %s." % workflow_id)

def init_modules2(request):
    init_modules()
    return HttpResponse("Loaded module definitions.")

# List all workflows, or create a new workflow.
@api_view(['GET', 'POST'])
@renderer_classes((JSONRenderer,))
def workflow_list(request, format=None):
    if request.method == 'GET':
        workflows = Workflow.objects.all()
        serializer = WorkflowSerializer(workflows, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = WorkflowSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
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

    try:
        moduleID = request.data['moduleID']
        insertBefore = request.data['insertBefore']
        module = Module.objects.get(pk=moduleID)
    except Workflow.DoesNotExist:
        return Response(status=status.HTTP_400_BAD_REQUEST)

    # create new WfModule, and increment order of every module below this in the workflow
    for wfm in WfModule.objects.filter(workflow=workflow):
        if wfm.order >= insertBefore:
            wfm.order += 1
            wfm.save()
    newwfm = WfModule.objects.create(workflow=workflow, module=module, order=insertBefore)
    newwfm.create_default_parameters()

    return Response(status=status.HTTP_204_NO_CONTENT)



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
def module_list(request, format=None):
    if request.method == 'GET':
        workflows = Module.objects.all()
        serializer = ModuleSerializer(workflows, many=True)
        return Response(serializer.data)

@api_view(['GET'])
@renderer_classes((JSONRenderer,))
def module_detail(request, pk, format=None):
    if request.method == 'GET':
        try:
            module = Module.objects.get(pk=pk)
        except Module.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = ModuleSerializer(module)
        return Response(serializer.data)
