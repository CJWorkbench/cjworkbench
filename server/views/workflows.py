from functools import lru_cache
from asgiref.sync import async_to_sync
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponseForbidden, JsonResponse
from django.template.response import TemplateResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import renderer_classes
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from server.minio import UserFilesBucket
from server.models import Module, ModuleVersion, Workflow
from server.models import AddModuleCommand, ReorderModulesCommand, \
        ChangeWorkflowTitleCommand
from server.serializers import WorkflowSerializer, ModuleSerializer, \
        WorkflowSerializerLite, WfModuleSerializer, UserSerializer
import server.utils
from server.versions import WorkflowUndo, WorkflowRedo

# This id_name->ids mapping is used by the client to execute the ADD STEP from table actions
# We cannot nix these, because modules without a UI in the stack (e.g. reorder) do not appear
# in the regular modules list in init_state, because that list is for the module menu
@lru_cache(maxsize=1)
def load_update_table_module_ids():
    modules = Module.objects.filter(id_name__in=[
        'duplicate-column',
        'editcells',
        'filter',
        'rename-columns',
        'reorder-columns',
        'sort-from-table',
        'duplicate-column',
        'selectcolumns',
        'extract-numbers',
        'clean-text',
        'convert-date',
        'convert-text'
    ])
    return dict([(m.id_name, m.id) for m in modules])


def make_init_state(request, workflow=None, modules=None):
    """Build a dict to embed as JSON in `window.initState` in HTML."""
    ret = {}

    if workflow:
        ret['workflowId'] = workflow.id
        ret['workflow'] = WorkflowSerializer(workflow,
                                             context={'request': request}).data
        wf_modules = workflow.wf_modules \
            .prefetch_related('parameter_vals__parameter_spec',
                              'module_version')
        wf_module_data_list = WfModuleSerializer(wf_modules, many=True).data
        ret['wfModules'] = dict([(str(wfm['id']), wfm)
                                 for wfm in wf_module_data_list])
        ret['selected_wf_module'] = workflow.selected_wf_module
        ret['uploadConfig'] = {
            'bucket': UserFilesBucket,
            'accessKey': settings.MINIO_ACCESS_KEY,  # never _SECRET_KEY
            'server': settings.MINIO_EXTERNAL_URL
        }
        ret['user_files_bucket'] = UserFilesBucket
        del ret['workflow']['selected_wf_module']

    if modules:
        modules_data_list = ModuleSerializer(modules, many=True).data
        ret['modules'] = dict([(str(m['id']), m) for m in modules_data_list])

    if request.user.is_authenticated():
        ret['loggedInUser'] = UserSerializer(request.user).data

    if workflow and not workflow.request_read_only(request):
        ret['updateTableModuleIds'] = load_update_table_module_ids()

    return ret


@login_required
def render_workflows(request):
    init_state = make_init_state(request)
    return TemplateResponse(request, 'workflows.html',
                            {'initState': init_state})


@api_view(['GET', 'POST'])
@login_required
@renderer_classes((JSONRenderer,))
def workflow_list(request, format=None):
    """List all workflows or create a new workflow."""
    if request.method == 'GET':
        workflows = Workflow.objects \
                .filter(Q(owner=request.user)
                        | Q(in_all_users_workflow_lists=True)) \
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
            server.utils.log_user_event(request, 'Opened Demo Workflow',
                                        {'name': workflow.name})
        return workflow.duplicate_anonymous(session_key)


# Restrict the modules that are available, based on the user
def visible_modules(request):
    # excluding because no functional UI
    if request.user.is_authenticated:
        return Module.objects.all()
    else:
        # need to log in to write Python code
        return Module.objects.exclude(id_name='pythoncode').all()


def _lookup_workflow_for_read(pk: int, request: HttpRequest) -> Workflow:
    """
    Find a Workflow based on its id.

    Raise Http404 if the Workflow does not exist and PermissionDenied if the
    workflow _does_ exist but the user does not have read access.
    """
    workflow = get_object_or_404(Workflow, pk=pk)

    if not workflow.request_authorized_read(request):
        raise PermissionDenied()

    return workflow


def _lookup_workflow_for_write(pk: int, request: HttpRequest) -> Workflow:
    """
    Find a Workflow based on its id.

    Raise Http404 if the Workflow does not exist and PermissionDenied if the
    workflow _does_ exist but the user does not have write access.
    """
    workflow = get_object_or_404(Workflow, pk=pk)

    if not workflow.request_authorized_write(request):
        raise PermissionDenied()

    return workflow


# no login_required as logged out users can view example/public workflows
def render_workflow(request, pk=None):
    workflow = _lookup_workflow_for_read(pk, request)

    if workflow.lesson and workflow.owner == request.user:
        return redirect(workflow.lesson)
    else:
        if workflow.example and workflow.owner != request.user:
            workflow = _get_anonymous_workflow_for(workflow, request)

        modules = visible_modules(request)
        init_state = make_init_state(request, workflow=workflow,
                                     modules=modules)

        return TemplateResponse(request, 'workflow.html',
                                {'initState': init_state})


# Retrieve or delete a workflow instance.
# Or reorder modules
@api_view(['GET', 'PATCH', 'POST', 'DELETE'])
@renderer_classes((JSONRenderer,))
def workflow_detail(request, pk, format=None):
    if request.method == 'GET':
        workflow = _lookup_workflow_for_read(pk, request)
        with workflow.cooperative_lock():
            data = make_init_state(request, workflow)
            return Response({
                'workflow': data['workflow'],
                'wfModules': data['wfModules'],
            })

    # We use PATCH to set the order of the modules when the user drags.
    elif request.method == 'PATCH':
        workflow = _lookup_workflow_for_write(pk, request)

        try:
            async_to_sync(ReorderModulesCommand.create)(workflow, request.data)
        except ValueError as e:
            # Caused by bad id or order keys not in range 0..n-1
            # (though they don't need to be sorted)
            return JsonResponse({'message': str(e), 'status_code': 400},
                                status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    elif request.method == 'POST':
        workflow = _lookup_workflow_for_write(pk, request)

        try:
            valid_fields = {'newName', 'public', 'selected_wf_module'}
            if not set(request.data.keys()).intersection(valid_fields):
                raise ValueError('Unknown fields: {}'.format(request.data))

            with workflow.cooperative_lock():
                if 'newName' in request.data:
                    async_to_sync(ChangeWorkflowTitleCommand.create)(
                        workflow,
                        request.data['newName']
                    )

                if 'public' in request.data:
                    # TODO this should be a command, so it's undoable
                    workflow.public = request.data['public']
                    workflow.save()

                if 'selected_wf_module' in request.data:
                    workflow.selected_wf_module = \
                            request.data['selected_wf_module']
                    workflow.save()

        except Exception as e:
            return JsonResponse({'message': str(e), 'status_code': 400},
                                status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    elif request.method == 'DELETE':
        workflow = _lookup_workflow_for_write(pk, request)
        workflow.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Invoked when user adds a module
@api_view(['PUT'])
@renderer_classes((JSONRenderer,))
def workflow_addmodule(request, pk, format=None):
    workflow = get_object_or_404(Workflow, pk=pk)

    if not workflow.request_authorized_write(request):
        return HttpResponseForbidden()

    module_id = int(request.data['moduleId'])
    index = int(request.data['index'])
    try:
        module = Module.objects.get(pk=module_id)
    except Module.DoesNotExist:
        return Response(status=status.HTTP_400_BAD_REQUEST)

    # don't allow python code module in anonymous workflow
    if module.id_name == 'pythoncode' and workflow.is_anonymous:
        return HttpResponseForbidden()

    # always add the latest version of a module (do we need ordering on the
    # objects to ensure last is always latest?)
    module_version = ModuleVersion.objects.filter(module=module).last()

    server.utils.log_user_event(request, 'ADD STEP ' + module.name, {
        'name': module.name,
        'id_name': module.id_name
    })

    delta = async_to_sync(AddModuleCommand.create)(workflow, module_version,
                                                   index)
    serializer = WfModuleSerializer(delta.wf_module)
    wfmodule_data = serializer.data

    return Response({
        'wfModule': wfmodule_data,
        'index': index,
    }, status.HTTP_201_CREATED)


# Duplicate a workflow. Returns new wf as json in same format as wf list
@api_view(['GET'])
@login_required
@renderer_classes((JSONRenderer,))
def workflow_duplicate(request, pk):
    workflow = _lookup_workflow_for_read(pk, request)

    workflow2 = workflow.duplicate(request.user)
    serializer = WorkflowSerializerLite(workflow2)

    server.utils.log_user_event(request, 'Duplicate Workflow',
                                {'name': workflow.name})

    return Response(serializer.data, status.HTTP_201_CREATED)


# Undo or redo
@api_view(['POST'])
@renderer_classes((JSONRenderer,))
def workflow_undo_redo(request, pk, action, format=None):
    workflow = _lookup_workflow_for_write(pk, request)

    if action == 'undo':
        async_to_sync(WorkflowUndo)(workflow)
    elif action == 'redo':
        async_to_sync(WorkflowRedo)(workflow)
    else:
        return JsonResponse({'message': '"action" must be "undo" or "redo"'},
                            status=status.HTTP_400_BAD_REQUEST)

    return Response(status=status.HTTP_204_NO_CONTENT)
