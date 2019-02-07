from asgiref.sync import async_to_sync
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpRequest, JsonResponse
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
from server.models import ModuleVersion, Workflow, WfModule
from server.serializers import WorkflowSerializer, ModuleSerializer, \
        TabSerializer, WorkflowSerializerLite, WfModuleSerializer, \
        UserSerializer
import server.utils
from .auth import lookup_workflow_for_write, \
        loads_workflow_for_read, lookup_workflow_for_owner


def make_init_state(request, workflow=None, modules=None):
    """Build a dict to embed as JSON in `window.initState` in HTML."""
    ret = {}

    if workflow:
        with workflow.cooperative_lock():
            ret['workflowId'] = workflow.id
            ret['workflow'] = WorkflowSerializer(
                workflow,
                context={'request': request}
            ).data

            tabs = list(workflow.live_tabs)
            ret['tabs'] = dict((str(tab.slug), TabSerializer(tab).data)
                               for tab in tabs)

            wf_modules = list(WfModule.live_in_workflow(workflow))

            ret['wfModules'] = dict((str(wfm.id), WfModuleSerializer(wfm).data)
                                    for wfm in wf_modules)

        ret['uploadConfig'] = {
            'bucket': minio.UserFilesBucket,
            'accessKey': settings.MINIO_ACCESS_KEY,  # never _SECRET_KEY
            'server': settings.MINIO_EXTERNAL_URL
        }
        ret['user_files_bucket'] = minio.UserFilesBucket

    if modules:
        modules_data_list = ModuleSerializer(modules, many=True).data
        ret['modules'] = dict([(str(m['id_name']), m)
                               for m in modules_data_list])

    if request.user.is_authenticated():
        ret['loggedInUser'] = UserSerializer(request.user).data

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
    """Create a new workflow."""
    workflow = Workflow.create_and_init(
        name='Untitled Workflow',
        owner=request.user,
        selected_tab_position=0
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
            server.utils.log_user_event_from_request(request,
                                                     'Opened Demo Workflow',
                                                     {'name': workflow.name})
        new_workflow = workflow.duplicate_anonymous(session_key)

        async_to_sync(new_workflow.last_delta.schedule_execute)()

        return new_workflow


def visible_modules(request):
    """Build a QuerySet of all ModuleVersions the user may use."""
    queryset = ModuleVersion.objects.all_latest()

    if not request.user.is_authenticated:
        # pythoncode is too obviously insecure
        queryset = queryset.exclude(id_name='pythoncode')

    return queryset


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

        if not workflow.are_all_render_results_fresh():
            # We're returning a Workflow that may have stale WfModules. That's
            # fine, but are we _sure_ the worker is about to render them? Let's
            # double-check. This will handle edge cases such as "we wiped our
            # caches" or maybe some bugs we haven't thought of.
            #
            # This isn't just for bug recovery. ChangeDataVersionCommand won't
            # queue_render until a client requests it.
            async_to_sync(rabbitmq.queue_render)(workflow.id,
                                                 workflow.last_delta_id)

        return TemplateResponse(request, 'workflow.html',
                                {'initState': init_state})


# Retrieve or delete a workflow instance.
# Or reorder modules
@api_view(['POST', 'DELETE'])
@renderer_classes((JSONRenderer,))
def workflow_detail(request, workflow_id, format=None):
    if request.method == 'POST':
        workflow = lookup_workflow_for_write(workflow_id, request)

        try:
            valid_fields = {'public'}
            if not set(request.data.keys()).intersection(valid_fields):
                raise ValueError('Unknown fields: {}'.format(request.data))

            if 'public' in request.data:
                # TODO this should be a command, so it's undoable
                workflow.public = request.data['public']
                workflow.save(update_fields=['public'])

        except Exception as e:
            return JsonResponse({'message': str(e), 'status_code': 400},
                                status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    elif request.method == 'DELETE':
        workflow = lookup_workflow_for_owner(workflow_id, request)
        workflow.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Duplicate a workflow. Returns new wf as json in same format as wf list
class Duplicate(View):
    @method_decorator(loads_workflow_for_read)
    def post(self, request: HttpRequest, workflow: Workflow):
        workflow2 = workflow.duplicate(request.user)
        serializer = WorkflowSerializerLite(workflow2,
                                            context={'request': request})

        server.utils.log_user_event_from_request(request,
                                                 'Duplicate Workflow',
                                                 {'name': workflow.name})

        async_to_sync(workflow2.last_delta.schedule_execute)()

        return JsonResponse(serializer.data, status=status.HTTP_201_CREATED)
