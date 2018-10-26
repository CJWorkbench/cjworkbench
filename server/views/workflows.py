from functools import lru_cache
from asgiref.sync import async_to_sync
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import F, Q
from django.http import HttpRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import renderer_classes
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from server import minio, rabbitmq
from server.models import Module, ModuleVersion, Workflow
from server.models.commands import AddModuleCommand, ReorderModulesCommand, \
        ChangeWorkflowTitleCommand
from server.serializers import WorkflowSerializer, ModuleSerializer, \
        WorkflowSerializerLite, WfModuleSerializer, UserSerializer
import server.utils
from server.versions import WorkflowUndo, WorkflowRedo
from .auth import lookup_workflow_for_read, lookup_workflow_for_write, \
        loads_workflow_for_read, loads_workflow_for_write, \
        lookup_workflow_for_owner


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
            'bucket': minio.UserFilesBucket,
            'accessKey': settings.MINIO_ACCESS_KEY,  # never _SECRET_KEY
            'server': settings.MINIO_EXTERNAL_URL
        }
        ret['user_files_bucket'] = minio.UserFilesBucket
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
    # Separate out workflows by type
    workflows = {}
    workflows['owned'] = Workflow.objects \
        .filter(owner=request.user) \
        .filter(Q(lesson_slug__isnull=True) | Q(lesson_slug=''))

    workflows['shared'] = Workflow.objects \
        .filter(acl__email=request.user.email) \
        .filter(Q(lesson_slug__isnull=True) | Q(lesson_slug=''))

    workflows['templates'] = Workflow.objects \
        .filter(in_all_users_workflow_lists=True) \
        .filter(Q(lesson_slug__isnull=True) | Q(lesson_slug=''))

    init_state = {
        'loggedInUser': UserSerializer(request.user).data,
        'workflows': {}
    }
    # turn queryset into list so we can sort it ourselves by reverse chron
    # (this is because 'last update' is a property of the delta, not the
    # Workflow. [2018-06-18, adamhooper] TODO make workflow.last_update a
    # column.
    for key, value in workflows.items():
        value = list(value)
        value.sort(key=lambda wf: wf.last_update(), reverse=True)
        serializer = WorkflowSerializerLite(value, many=True,
                                            context={'request': request})
        init_state['workflows'][key] = serializer.data

    return TemplateResponse(request, 'workflows.html',
                            {'initState': init_state})


@api_view(['POST'])
@login_required
@renderer_classes((JSONRenderer,))
def workflow_list(request, format=None):
    """List all workflows or create a new workflow."""
    workflow = Workflow.objects.create(
        name='New Workflow',
        owner=request.user
    )
    serializer = WorkflowSerializerLite(workflow,
                                        context={'request': request})
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
        new_workflow = workflow.duplicate_anonymous(session_key)

        async_to_sync(new_workflow.last_delta.schedule_execute)()

        return new_workflow


# Restrict the modules that are available, based on the user
def visible_modules(request):
    # excluding because no functional UI
    if request.user.is_authenticated:
        return Module.objects.all()
    else:
        # need to log in to write Python code
        return Module.objects.exclude(id_name='pythoncode').all()


# no login_required as logged out users can view example/public workflows
@loads_workflow_for_read
def render_workflow(request: HttpRequest, workflow: Workflow):
    if workflow.lesson and workflow.owner == request.user:
        return redirect(workflow.lesson)
    else:
        if workflow.example and workflow.owner != request.user:
            workflow = _get_anonymous_workflow_for(workflow, request)

        modules = visible_modules(request)
        init_state = make_init_state(request, workflow=workflow,
                                     modules=modules)

        if workflow.wf_modules.exclude(
            last_relevant_delta_id=F('cached_render_result_delta_id')
        ).exists():
            # We're returning a Workflow that may have stale WfModules. That's
            # fine, but are we _sure_ the worker is about to render them? Let's
            # double-check. This will handle edge cases such as "we wiped our
            # caches" or maybe some bugs we haven't thought of.
            #
            # Normally this is a race and this render is spurious. TODO prevent
            # two workers from rendering the same workflow at the same time.
            rabbitmq.queue_render(workflow)

        return TemplateResponse(request, 'workflow.html',
                                {'initState': init_state})


# Retrieve or delete a workflow instance.
# Or reorder modules
@api_view(['GET', 'PATCH', 'POST', 'DELETE'])
@renderer_classes((JSONRenderer,))
def workflow_detail(request, workflow_id, format=None):
    if request.method == 'GET':
        workflow = lookup_workflow_for_read(workflow_id, request)
        with workflow.cooperative_lock():
            data = make_init_state(request, workflow)
            return Response({
                'workflow': data['workflow'],
                'wfModules': data['wfModules'],
            })

    # We use PATCH to set the order of the modules when the user drags.
    elif request.method == 'PATCH':
        workflow = lookup_workflow_for_write(workflow_id, request)

        try:
            async_to_sync(ReorderModulesCommand.create)(workflow, request.data)
        except ValueError as e:
            # Caused by bad id or order keys not in range 0..n-1
            # (though they don't need to be sorted)
            return Response({'message': str(e), 'status_code': 400},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    elif request.method == 'POST':
        workflow = lookup_workflow_for_write(workflow_id, request)

        try:
            valid_fields = {'newName', 'public', 'selected_wf_module'}
            if not set(request.data.keys()).intersection(valid_fields):
                raise ValueError('Unknown fields: {}'.format(request.data))

            if 'newName' in request.data:
                async_to_sync(ChangeWorkflowTitleCommand.create)(
                    workflow,
                    request.data['newName']
                )

            if 'public' in request.data:
                # TODO this should be a command, so it's undoable
                workflow.public = request.data['public']
                workflow.save(update_fields=['public'])

            if 'selected_wf_module' in request.data:
                workflow.selected_wf_module = \
                        request.data['selected_wf_module']
                workflow.save(update_fields=['selected_wf_module'])

        except Exception as e:
            return JsonResponse({'message': str(e), 'status_code': 400},
                                status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    elif request.method == 'DELETE':
        workflow = lookup_workflow_for_owner(workflow_id, request)
        workflow.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Invoked when user adds a module
@api_view(['PUT'])
@loads_workflow_for_write
def workflow_addmodule(request: HttpRequest, workflow: Workflow):
    module_id = int(request.data['moduleId'])
    index = int(request.data['index'])
    try:
        module = Module.objects.get(pk=module_id)
    except Module.DoesNotExist:
        return Response(status=status.HTTP_400_BAD_REQUEST)

    try:
        values = dict(request.data['values'])
    except KeyError:
        values = {}
    except TypeError:
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
                                                   index, values)
    serializer = WfModuleSerializer(delta.wf_module)
    wfmodule_data = serializer.data

    return Response({
        'wfModule': wfmodule_data,
        'index': index,
    }, status.HTTP_201_CREATED)


# Duplicate a workflow. Returns new wf as json in same format as wf list
class Duplicate(View):
    @method_decorator(loads_workflow_for_read)
    def post(self, request: HttpRequest, workflow: Workflow):
        workflow2 = workflow.duplicate(request.user)
        serializer = WorkflowSerializerLite(workflow2,
                                            context={'request': request})

        server.utils.log_user_event(request, 'Duplicate Workflow',
                                    {'name': workflow.name})

        async_to_sync(workflow2.last_delta.schedule_execute)()

        return JsonResponse(serializer.data, status=status.HTTP_201_CREATED)


# Undo or redo
@api_view(['POST'])
@loads_workflow_for_write
def workflow_undo_redo(request: HttpRequest, workflow: Workflow, action):
    if action == 'undo':
        async_to_sync(WorkflowUndo)(workflow)
    elif action == 'redo':
        async_to_sync(WorkflowRedo)(workflow)
    else:
        return JsonResponse({'message': '"action" must be "undo" or "redo"'},
                            status=status.HTTP_400_BAD_REQUEST)

    return Response(status=status.HTTP_204_NO_CONTENT)
