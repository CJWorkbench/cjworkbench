from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from django.template.response import TemplateResponse
from django.contrib.auth.decorators import login_required
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import renderer_classes
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from server.models import Module, ModuleVersion, Workflow, WfModule, ParameterSpec, ParameterVal
from server.serializers import WorkflowSerializer, WorkflowSerializerLite
from server.execute import execute_wfmodule


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
        serializer = WorkflowSerializerLite(workflows, many=True)
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
        #For now, we always get the last version of a module – the ModuleVersion object is ordered by the
        # last_update_time, so retrieving the 0th element will return the latest version.
        #In future versions, we'll need to be cleverer here (but only marginally so): we should always add the
        #latest version of a workflow, and if the users want to use a previous version, they should be able to rollback
        #using the module UI, and not from the "Add Module" UI. This will require API changes.
        module_version = ModuleVersion.objects.filter(module=module)[0]
    except Module.DoesNotExist:
        return Response(status=status.HTTP_400_BAD_REQUEST)

    # create new WfModule in the right place
    # this also makes wfm.order sequential, which is not strictly necessary but kinda nice
    pos = 0
    for wfm in WfModule.objects.filter(workflow=workflow):
        if pos == insertBefore:
            pos += 1
        if wfm.order != pos:
            wfm.order = pos
            wfm.save()
        pos +=1

    newwfm = WfModule.objects.create(workflow=workflow, module_version=module_version, order=insertBefore)
    newwfm.create_default_parameters()

    return Response(status=status.HTTP_204_NO_CONTENT)

