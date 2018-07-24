from django.http import HttpRequest, HttpResponseForbidden, HttpResponseNotFound
from django.template.response import TemplateResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import renderer_classes
from rest_framework.decorators import permission_classes
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from server.utils import *
from server.models import Module, ModuleVersion, Workflow
from server.models import AddModuleCommand, ReorderModulesCommand, ChangeWorkflowTitleCommand
from server.serializers import WorkflowSerializer, ModuleSerializer, WorkflowSerializerLite, WfModuleSerializer, UserSerializer
from server.versions import WorkflowUndo, WorkflowRedo

# Add module name to expected Id alias {module_name: module_alias?}
modules_from_table = [
    'editcells',
    'filter',
    'sort-from-table',
    'reorder-columns',
    'rename-columns',
    'duplicate-column',
    'selectcolumns'
]

# Cache module Ids dynamically per keys in module_name_to_id
# because we need it on every Workflow page load, and it never changes
def module_id(id_name):
    if module_ids[id_name] is None:
        try:
            module = Module.objects.filter(id_name=id_name).first()
            if not module:
                module_ids[id_name] = None
            else:
                module_ids[id_name] = module.id
        except Module.DoesNotExist:
            return None

    return module_ids[id_name]

module_ids = {id: None for id in modules_from_table}

# Data that is embedded in the initial HTML, so we don't need to call back server for it
def make_init_state(request, workflow=None, modules=None):
    ret = {}

    if workflow:
        ret['workflowId'] = workflow.id
        ret['workflow'] = WorkflowSerializer(workflow, context={'request' : request}).data
        ret['selected_wf_module'] = workflow.selected_wf_module
        del ret['workflow']['selected_wf_module']

    if modules:
        ret['modules'] = ModuleSerializer(modules, many=True).data

    if request.user.is_authenticated():
        ret['loggedInUser'] = UserSerializer(request.user).data

    if workflow and not workflow.request_read_only(request):
        ret['updateTableModuleIds'] = {}
        for id_name in modules_from_table:
            # Simplify for front end retrieval by module name
            ret['updateTableModuleIds'][id_name] = module_id(id_name)

    return ret

# ---- Workflows list page ----

@login_required
def render_workflows(request):
    init_state = make_init_state(request)
    return TemplateResponse(request, 'workflows.html',
                            {'initState': init_state})

# List all workflows, or create a new workflow.
@api_view(['GET', 'POST'])
@login_required
@renderer_classes((JSONRenderer,))
def workflow_list(request, format=None):
    if request.method == 'GET':
        workflows = Workflow.objects \
                .filter(Q(owner=request.user) | Q(example=True)) \
                .filter(Q(lesson_slug__isnull=True) | Q(lesson_slug=''))

        # turn queryset into list so we can sort it ourselves by reverse chron
        # (this is because 'last update' is a property of the delta, not the
        # Workflow. [2018-06-18, adamhooper] TODO make workflow.last_update a
        # column.
        workflows = list(workflows)
        workflows.sort(key=lambda wf: wf.last_update(), reverse=True)

        serializer = WorkflowSerializerLite(workflows, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        workflow = Workflow.objects.create(
            name='New Workflow',
            owner=request.user
        )
        serializer = WorkflowSerializerLite(workflow)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ---- Workflow ----


def _get_anonymous_workflow_for(workflow: Workflow,
                                request: HttpRequest) -> Workflow:
    """If not owner, return a cached duplicate of `workflow`.

    The duplicate will be married to `request.session.session_key`, and its
    `.is_anonymous` will return `True`.
    """
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key

    try:
        return Workflow.objects.get(original_workflow_id=workflow.id,
                                    anonymous_owner_session_key=session_key)
    except Workflow.DoesNotExist:
        if workflow.example:
            log_user_event(request.user,
                           'Opened Demo Workflow',
                           {'name': workflow.name})
        return workflow.duplicate_anonymous(session_key)


# Restrict the modules that are available, based on the user
def visible_modules(request):
    modules = Module.objects.all().exclude(id_name='reorder-columns') # excluding because no functional UI
    if request.user.is_authenticated:
        return modules
    else:
        return modules.exclude(id_name='pythoncode')  # need to log in to write Python code


# no login_required as logged out users can view example/public workflows
def render_workflow(request, pk=None):
    # Workflow must exist and be readable by this user
    workflow = get_object_or_404(Workflow, pk=pk)

    # 404 if trying to access an object without even read authorization, to prevent leakage of object ids
    if not workflow.request_authorized_read(request):
        return HttpResponseNotFound()

    if workflow.lesson and workflow.owner == request.user:
        return redirect(workflow.lesson)
    else:
        if workflow.example and workflow.owner != request.user:
            workflow = _get_anonymous_workflow_for(workflow, request)

        modules = visible_modules(request)
        init_state = make_init_state(request, workflow=workflow, modules=modules)

        return TemplateResponse(request, 'workflow.html',
                                {'initState': init_state})


# Retrieve or delete a workflow instance.
# Or reorder modules
@api_view(['GET', 'PATCH', 'POST', 'DELETE'])
@renderer_classes((JSONRenderer,))
def workflow_detail(request, pk, format=None):
    workflow = get_object_or_404(Workflow, pk=pk)

    # 404 if trying to access an object without even read authorization, to prevent leakage of object ids
    if not workflow.request_authorized_read(request):
        return HttpResponseNotFound()

    if request.method == 'GET':
        with workflow.cooperative_lock():
            serializer = WorkflowSerializer(workflow,
                                            context={'request': request})
            return Response(serializer.data)

    # We use PATCH to set the order of the modules when the user drags.
    elif request.method == 'PATCH':
        if not workflow.request_authorized_write(request):
            return HttpResponseForbidden()

        try:
            ReorderModulesCommand.create(workflow, request.data)
        except ValueError as e:
            # Caused by bad id or order keys not in range 0..n-1 (though they don't need to be sorted)
            return Response({'message': str(e), 'status_code':400}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    elif request.method == 'POST':
        if not workflow.request_authorized_write(request):
            return HttpResponseForbidden()

        try:
            if not set(request.data.keys()).intersection({"newName", "public", "selected_wf_module"}):
                raise ValueError('Unknown fields: {}'.format(request.data))

            with workflow.cooperative_lock():
                if 'newName' in request.data:
                    ChangeWorkflowTitleCommand.create(workflow, request.data['newName'])

                if 'public' in request.data:
                    # TODO this should be a command, so it's undoable
                    workflow.public = request.data['public']
                    workflow.save()

                if 'selected_wf_module' in request.data:
                    workflow.selected_wf_module = request.data['selected_wf_module']
                    workflow.save()

        except Exception as e:
            return Response({'message': str(e), 'status_code':400}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    elif request.method == 'DELETE':
        if not workflow.request_authorized_write(request):
            return HttpResponseForbidden()

        workflow.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Invoked when user adds a module
@api_view(['PUT'])
@renderer_classes((JSONRenderer,))
def workflow_addmodule(request, pk, format=None):
    workflow = get_object_or_404(Workflow, pk=pk)

    if not workflow.request_authorized_write(request):
        return HttpResponseForbidden()

    module_id = request.data['moduleId']
    insert_before = int(request.data['insertBefore'])
    try:
        module = Module.objects.get(pk=module_id)
    except Module.DoesNotExist:
        return Response(status=status.HTTP_400_BAD_REQUEST)

    # don't allow python code module in anonymous workflow
    if module.id_name == 'pythoncode' and workflow.is_anonymous:
        return HttpResponseForbidden()

    # always add the latest version of a module (do we need ordering on the objects to ensure last is always latest?)
    module_version = ModuleVersion.objects.filter(module=module).last()

    log_user_event(request.user, 'Add Module ' + module.name, {'name': module.name, 'id_name':module.id_name})

    delta = AddModuleCommand.create(workflow, module_version, insert_before)
    serializer = WfModuleSerializer(delta.wf_module)
    wfmodule_data = serializer.data
    wfmodule_data['insert_before'] = request.data['insertBefore']

    return Response(wfmodule_data, status.HTTP_201_CREATED)


# Duplicate a workflow. Returns new wf as json in same format as wf list
@api_view(['GET'])
@login_required
@renderer_classes((JSONRenderer,))
def workflow_duplicate(request, pk):
    try:
        workflow = Workflow.objects.get(pk=pk)
    except Workflow.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if not workflow.request_authorized_read(request):
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

    if not workflow.request_authorized_write(request):
        return HttpResponseForbidden()

    if action=='undo':
        WorkflowUndo(workflow)
    elif action=='redo':
        WorkflowRedo(workflow)

    return Response(status=status.HTTP_204_NO_CONTENT)
