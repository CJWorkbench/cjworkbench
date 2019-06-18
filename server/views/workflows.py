from __future__ import annotations
from dataclasses import dataclass
import datetime
from typing import List
from asgiref.sync import async_to_sync
from django.conf import settings
from django.contrib.auth.decorators import login_required
import django.db
from django.db.models import Q
from django.http import Http404, HttpRequest, JsonResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import renderer_classes
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from server import minio, rabbitmq
from server.models import ModuleVersion, Workflow, WfModule, Tab
from server.models.course import CourseLookup
from server.models.lesson import LessonLookup
from server.serializers import WorkflowSerializer, ModuleSerializer, \
        TabSerializer, WorkflowSerializerLite, WfModuleSerializer, \
        UserSerializer
import server.utils
from server.settingsutils import workbench_user_display
from .auth import lookup_workflow_for_write, loads_workflow_for_read


def make_init_state(request, workflow=None, modules=None):
    """
    Build a dict to embed as JSON in `window.initState` in HTML.

    Raise Http404 if the workflow disappeared.

    Side-effect: update workflow.last_viewed_at.
    """
    ret = {}

    if workflow:
        try:
            with workflow.cooperative_lock():  # raise DoesNotExist on race
                ret['workflowId'] = workflow.id
                ret['workflow'] = WorkflowSerializer(
                    workflow,
                    context={'request': request}
                ).data

                tabs = list(workflow.live_tabs)
                ret['tabs'] = dict((str(tab.slug), TabSerializer(tab).data)
                                   for tab in tabs)

                wf_modules = list(WfModule.live_in_workflow(workflow))

                ret['wfModules'] = {str(wfm.id): WfModuleSerializer(wfm).data
                                    for wfm in wf_modules}
                workflow.last_viewed_at = timezone.now()
                workflow.save(update_fields=['last_viewed_at'])
        except Workflow.DoesNotExist:
            raise Http404('Workflow was recently deleted')

    if modules:
        modules_data_list = ModuleSerializer(modules, many=True).data
        ret['modules'] = dict([(str(m['id_name']), m)
                               for m in modules_data_list])

    if request.user.is_authenticated:
        ret['loggedInUser'] = UserSerializer(request.user).data

    return ret


class Index(View):
    @method_decorator(login_required)
    def post(self, request: HttpRequest):
        """Create a new workflow."""
        workflow = Workflow.create_and_init(
            name='Untitled Workflow',
            owner=request.user,
            selected_tab_position=0
        )
        return redirect('/workflows/%d/' % workflow.id)

    @method_decorator(login_required)
    def get(self, request: HttpRequest):
        """Render workflow-list page."""
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


def _get_anonymous_workflow_for(workflow: Workflow,
                                request: HttpRequest) -> Workflow:
    """
    If not owner, return a cached duplicate of `workflow`.

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
        try:
            new_workflow = workflow.duplicate_anonymous(session_key)
        except django.db.IntegrityError:
            # Race: the same user just requested a duplicate at the same time,
            # and both decided to duplicate simultaneously. A database
            # constraint means one will get an IntegrityError ... so at this
            # point we can assume our original query will succeed.
            return Workflow.objects.get(
                original_workflow_id=workflow.id,
                anonymous_owner_session_key=session_key
            )


        async_to_sync(rabbitmq.queue_render)(new_workflow.id,
                                             new_workflow.last_delta_id)
        if workflow.example:
            server.utils.log_user_event_from_request(request,
                                                     'Opened Demo Workflow',
                                                     {'name': workflow.name})

        return new_workflow


def visible_modules(request):
    """
    Load all ModuleVersions the user may use.
    """
    ret = ModuleVersion.objects.get_all_latest()

    if not request.user.is_authenticated:
        ret = [mv for mv in ret if mv.id_name != 'pythoncode']

    return ret


def _lesson_exists(slug):
    if '/' in slug:
        course_slug, lesson_slug = slug.split('/')
        try:
            course = CourseLookup[course_slug]
        except KeyError:
            return False
        return lesson_slug in course.lessons
    else:
        return slug in LessonLookup


# no login_required as logged out users can view example/public workflows
@loads_workflow_for_read
def render_workflow(request: HttpRequest, workflow: Workflow):
    if (
        workflow.lesson_slug
        and _lesson_exists(workflow.lesson_slug)
        and workflow.owner == request.user
    ):
        if '/' in workflow.lesson_slug:
            # /courses/a-course/a-lesson -- no trailing '/' because courses use
            # relative URLs
            return redirect('/courses/' + workflow.lesson_slug)
        else:
            # /lessons/a-lesson/
            return redirect('/lessons/' + workflow.lesson_slug)
    else:
        if workflow.example and workflow.owner != request.user:
            workflow = _get_anonymous_workflow_for(workflow, request)

        modules = visible_modules(request)
        init_state = make_init_state(request, workflow=workflow,
                                     modules=modules)

        if not workflow.are_all_render_results_fresh():
            # We're returning a Workflow that may have stale WfModules. That's
            # fine, but are we _sure_ the renderer is about to render them?
            # Let's double-check. This will handle edge cases such as "we wiped
            # our caches" or maybe some bugs we haven't thought of.
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

        valid_fields = {'public'}
        if not set(request.data.keys()).intersection(valid_fields):
            return JsonResponse({
                'message': 'Unknown fields: %r' % request.data,
                'status_code': 400,
            }, status=status.HTTP_400_BAD_REQUEST)
        if 'public' in request.data:
            workflow.public = bool(request.data['public'])
            workflow.save(update_fields=['public'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    elif request.method == 'DELETE':
        try:
            with Workflow.authorized_lookup_and_cooperative_lock(
                'owner',
                request.user,
                request.session,
                pk=workflow_id
            ) as workflow:
                workflow.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Workflow.DoesNotExist as err:
            if err.args[0] == 'owner access denied':
                return JsonResponse({
                    'message': str(err),
                    'status_code': 403,
                }, status=status.HTTP_403_FORBIDDEN)
            else:
                return JsonResponse({
                    'message': 'Workflow not found',
                    'status_code': 404,
                }, status=status.HTTP_404_NOT_FOUND)


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

        async_to_sync(rabbitmq.queue_render)(workflow2.id,
                                             workflow2.last_delta_id)

        return JsonResponse(serializer.data, status=status.HTTP_201_CREATED)


class Report(View):
    """Render all the charts in a workflow."""
    @dataclass
    class WfModuleWithIframe:
        id: int
        delta_id: int

        @classmethod
        def from_wf_module(cls,
                           wf_module: WfModule) -> Report.WfModuleWithIframe:
            return cls(
                id=wf_module.id,
                delta_id=wf_module.last_relevant_delta_id
            )

    @dataclass
    class TabWithIframes:
        slug: str
        name: str
        wf_modules: List[Report.WfModuleWithIframe]

        @classmethod
        def from_tab(cls, tab: Tab) -> Report.TabWithIframes:
            all_wf_modules = (
                tab.live_wf_modules
                .only('id', 'last_relevant_delta_id', 'module_id_name')
            )

            wf_modules = [Report.WfModuleWithIframe.from_wf_module(wf_module)
                          for wf_module in all_wf_modules
                          if wf_module.module_version.html_output]
            return cls(
                slug=tab.slug,
                name=tab.name,
                wf_modules=wf_modules
            )

    @dataclass
    class ReportWorkflow:
        id: int
        name: str
        owner_name: str
        updated_at: datetime.datetime
        tabs: List[Report.TabWithIframes]

        @classmethod
        def from_workflow(cls, workflow: Workflow) -> Report.ReportWorkflow:
            # prefetch would be nice, but it's tricky because A) we need to
            # filter out is_deleted; and B) we need to filter out
            # ModuleVersions without .html_output.
            all_tabs = [Report.TabWithIframes.from_tab(tab)
                        for tab in workflow.live_tabs]
            tabs = [tab for tab in all_tabs if tab.wf_modules]
            return cls(
                id=workflow.id,
                name=workflow.name,
                owner_name=workbench_user_display(workflow.owner),
                updated_at=workflow.last_update(),
                tabs=tabs
            )


    @method_decorator(loads_workflow_for_read)
    def get(self, request: HttpRequest, workflow: Workflow):
        report_workflow = Report.ReportWorkflow.from_workflow(workflow)
        return TemplateResponse(request, 'report.html',
                                {'workflow': report_workflow})
