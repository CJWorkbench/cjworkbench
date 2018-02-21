from django.http import HttpResponseForbidden, Http404
from django.template.response import TemplateResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import renderer_classes
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from server.utils import *
from server.models import Module, ModuleVersion, Workflow
from server.models import AddModuleCommand, ReorderModulesCommand, ChangeWorkflowTitleCommand
from server.serializers import WorkflowSerializer, WorkflowSerializerLite, WfModuleSerializer, UserSerializer
from server.versions import WorkflowUndo, WorkflowRedo
from django.db.models import Q
import json

# Cache this because we need it on every Workflow page load, and it never changes
def edit_cells_module_id():
    if edit_cells_module_id.id is None:
        try:
            edit_cells_module_id.id = Module.objects.get(id_name='editcells').id
        except Module.DoesNotExist:
            return None     # should only happen in testing

    return edit_cells_module_id.id

edit_cells_module_id.id = None

# Data that is embedded in the initial HTML, so we don't need to call back server for it
def make_init_state(request):
    if request.user.is_authenticated():
        user = UserSerializer(request.user)
        edit_cells_module = edit_cells_module_id()
        init_state = {
            'loggedInUser': user.data,
            'editCellsModuleId' : edit_cells_module
        }
        return json.dumps(init_state)
    else:
        return '{}'

# ---- Workflows list page ----

@login_required
def render_workflows(request):
    init_state = make_init_state(request)
    return TemplateResponse(request, 'workflows.html', {'initState': init_state})

# List all workflows, or create a new workflow.
@api_view(['GET', 'POST'])
@renderer_classes((JSONRenderer,))
def workflow_list(request, format=None):
    if request.method == 'GET':
        workflows = Workflow.objects.filter(Q(owner=request.user))

        # turn queryset into array so we can sort it ourselves by reverse chron
        workflows = workflows.all()
        workflows = sorted(workflows, key=lambda wf: wf.last_update(), reverse=True)

        serializer = WorkflowSerializerLite(workflows, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = WorkflowSerializer(data=request.data, context={'user': request.user})
        if serializer.is_valid():
            serializer.save(owner=request.user)
            log_user_event(request.user, 'Create Workflow')
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---- Workflow ----

# no login_required as logged out users can view public workflows
def render_workflow(request, pk=None):
    # Workflow must exist and be readable by this user
    workflow = get_object_or_404(Workflow, pk=pk)

    if not workflow.user_authorized_read(request.user):
        raise Http404()

    init_state = make_init_state(request)
    return TemplateResponse(request, 'workflow.html', {'initState': init_state})


# Retrieve or delete a workflow instance.
# Or reorder modules
@api_view(['GET', 'PATCH', 'POST', 'DELETE'])
@renderer_classes((JSONRenderer,))
@permission_classes((IsAuthenticatedOrReadOnly, ))
def workflow_detail(request, pk, format=None):

    workflow = get_object_or_404(Workflow, pk=pk)

    if not workflow.user_authorized_read(request.user):
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = WorkflowSerializer(workflow, context={'user' : request.user})
        return Response(serializer.data)

    # We use PATCH to set the order of the modules when the user drags.
    elif request.method == 'PATCH':
        if not workflow.user_authorized_write(request.user):
            return HttpResponseForbidden()

        try:
            ReorderModulesCommand.create(workflow, request.data)
        except ValueError as e:
            # Caused by bad id or order keys not in range 0..n-1 (though they don't need to be sorted)
            return Response({'message': str(e), 'status_code':400}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    elif request.method == 'POST':
        if not workflow.user_authorized_write(request.user):
            return HttpResponseForbidden()

        try:
            if not set(request.data.keys()).intersection({"newName", "public", "module_library_collapsed", "selected_wf_module"}):
                raise ValueError('Unknown fields: {}'.format(request.data))

            if 'newName' in request.data:
                ChangeWorkflowTitleCommand.create(workflow, request.data['newName'])

            if 'public' in request.data:
                # TODO this should be a command, so it's undoable
                workflow.public = request.data['public']
                workflow.save()

            if 'module_library_collapsed' in request.data:
                workflow.module_library_collapsed = request.data['module_library_collapsed']
                workflow.save()

            if 'selected_wf_module' in request.data:
                workflow.selected_wf_module = request.data['selected_wf_module']
                workflow.save()

        except Exception as e:
            return Response({'message': str(e), 'status_code':400}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    elif request.method == 'DELETE':
        if not workflow.user_authorized_write(request.user):
            return HttpResponseForbidden()

        workflow.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Invoked when user adds a module
@api_view(['PUT'])
@renderer_classes((JSONRenderer,))
def workflow_addmodule(request, pk, format=None):

    workflow = get_object_or_404(Workflow, pk=pk)

    if not workflow.user_authorized_write(request.user):
        return HttpResponseForbidden()

    module_id = request.data['moduleId']
    insert_before = int(request.data['insertBefore'])
    try:
        module = Module.objects.get(pk=module_id)
    except Module.DoesNotExist:
        return Response(status=status.HTTP_400_BAD_REQUEST)

    # always add the latest version of a module (do we need ordering on the objects to ensure last is always latest?)
    module_version = ModuleVersion.objects.filter(module=module).last()

    log_user_event(request.user, 'Add Module', {'name': module.name, 'id_name':module.id_name})

    delta = AddModuleCommand.create(workflow, module_version, insert_before)
    serializer = WfModuleSerializer(delta.wf_module)
    wfmodule_data = serializer.data
    wfmodule_data['insert_before'] = request.data['insertBefore']

    return Response(wfmodule_data, status.HTTP_201_CREATED)


# Duplicate a workflow. Returns new wf as json in same format as wf list
@api_view(['GET'])
@renderer_classes((JSONRenderer,))
def workflow_duplicate(request, pk):
    try:
        workflow = Workflow.objects.get(pk=pk)
    except Workflow.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if not workflow.user_authorized_read(request.user):
        return HttpResponseForbidden()

    workflow2 = workflow.duplicate(request.user)
    serializer = WorkflowSerializerLite(workflow2)

    log_user_event(request.user, 'Duplicate Workflow', {'name':workflow.name})

    return Response(serializer.data, status.HTTP_201_CREATED)


# Undo or redo
@api_view(['PUT'])
@renderer_classes((JSONRenderer,))
def workflow_undo_redo(request, pk, action, format=None):
    try:
        workflow = Workflow.objects.get(pk=pk)
    except Workflow.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if not workflow.user_authorized_write(request.user):
        return HttpResponseForbidden()

    if action=='undo':
        WorkflowUndo(workflow)
    elif action=='redo':
        WorkflowRedo(workflow)

    return Response(status=status.HTTP_204_NO_CONTENT)
