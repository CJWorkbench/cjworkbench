from __future__ import annotations
from dataclasses import dataclass
import datetime
import json
from typing import Any, Dict, List, Optional
from asgiref.sync import async_to_sync
from django.contrib.auth.decorators import login_required
import django.db
from django.db.models import Q
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework import status
from cjwstate import clientside, rabbitmq
from cjwstate.models import Workflow, WfModule, Tab
from cjwstate.models.module_registry import MODULE_REGISTRY
from cjwstate.modules.types import ModuleZipfile
from server.models.course import CourseLookup
from server.models.lesson import LessonLookup
from server.serializers import (
    JsonizeContext,
    jsonize_clientside_init,
    jsonize_user,
    jsonize_clientside_workflow,
)
import server.utils
from server.settingsutils import workbench_user_display
from .auth import loads_workflow_for_read, loads_workflow_for_write
from cjworkbench.i18n import default_locale


def make_init_state(
    request, workflow: Workflow, modules: Dict[str, ModuleZipfile]
) -> Dict[str, Any]:
    """
    Build a dict to embed as JSON in `window.initState` in HTML.

    Raise Http404 if the workflow disappeared.

    Side-effect: update workflow.last_viewed_at.
    """
    try:
        with workflow.cooperative_lock():  # raise DoesNotExist on race
            workflow.last_viewed_at = timezone.now()
            workflow.save(update_fields=["last_viewed_at"])

            state = clientside.Init(
                workflow=workflow.to_clientside(),
                tabs={tab.slug: tab.to_clientside() for tab in workflow.live_tabs},
                steps={
                    step.id: step.to_clientside()
                    for step in WfModule.live_in_workflow(workflow)
                },
                modules={
                    module_id: clientside.Module(
                        spec=module.get_spec(),
                        js_module=module.get_optional_js_module(),
                    )
                    for module_id, module in modules.items()
                },
            )
    except Workflow.DoesNotExist:
        raise Http404("Workflow was recently deleted")

    ctx = JsonizeContext(request.user, request.session, request.locale_id)
    return jsonize_clientside_init(state, ctx)


class Index(View):
    @method_decorator(login_required)
    def post(self, request: HttpRequest):
        """Create a new workflow."""
        workflow = Workflow.create_and_init(
            name="Untitled Workflow", owner=request.user, selected_tab_position=0
        )
        return redirect("/workflows/%d/" % workflow.id)

    @method_decorator(login_required)
    def get(self, request: HttpRequest):
        """Render workflow-list page."""

        ctx = JsonizeContext(request.user, request.session, request.locale_id)

        def list_workflows_as_json(**kwargs) -> List[Dict[str, Any]]:
            workflows = (
                Workflow.objects.filter(**kwargs)
                .prefetch_related("acl", "owner", "last_delta")
                .order_by("-last_delta__datetime")
                .filter(Q(lesson_slug__isnull=True) | Q(lesson_slug=""))
            )
            return [
                jsonize_clientside_workflow(
                    w.to_clientside(include_tab_slugs=False), ctx, is_init=True
                )
                for w in workflows
            ]

        init_state = {
            "loggedInUser": jsonize_user(request.user),
            "workflows": {
                "owned": list_workflows_as_json(owner=request.user),
                "shared": list_workflows_as_json(acl__email=request.user.email),
                "templates": list_workflows_as_json(in_all_users_workflow_lists=True),
            },
        }

        return TemplateResponse(request, "workflows.html", {"initState": init_state})


def _get_anonymous_workflow_for(workflow: Workflow, request: HttpRequest) -> Workflow:
    """
    If not owner, return a cached duplicate of `workflow`.

    The duplicate will be married to `request.session.session_key`, and its
    `.is_anonymous` will return `True`.
    """
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key

    try:
        return Workflow.objects.get(
            original_workflow_id=workflow.id, anonymous_owner_session_key=session_key
        )
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
                anonymous_owner_session_key=session_key,
            )

        async_to_sync(rabbitmq.queue_render)(
            new_workflow.id, new_workflow.last_delta_id
        )
        if workflow.example:
            server.utils.log_user_event_from_request(
                request, "Opened Demo Workflow", {"name": workflow.name}
            )

        return new_workflow


def visible_modules(request) -> Dict[str, ModuleZipfile]:
    """
    Load all ModuleZipfiles the user may use.
    """
    ret = dict(MODULE_REGISTRY.all_latest())  # shallow copy

    if not request.user.is_authenticated:
        del ret["pythoncode"]

    return ret


def _lesson_redirect_url(slug) -> Optional[str]:
    *other, lesson_slug = slug.split("/")

    if not other:  # compatibility case: only lesson_slug with no locale_id
        new_slug = default_locale + "/" + slug
        return "/lessons/" + new_slug if new_slug in LessonLookup else None

    if len(other) == 2:  # locale_id/course_slug/lesson_slug
        try:
            course = CourseLookup["/".join(other)]
        except KeyError:
            return None
        return "/courses/" + slug if lesson_slug in course.lessons else None

    try:  # compatibility case: course_slug/lesson_slug with no locale_id
        new_slug = default_locale + "/" + other[0]
        course = CourseLookup[new_slug]
        return (
            "/courses/" + new_slug + "/" + lesson_slug
            if lesson_slug in course.lessons
            else None
        )
    except KeyError:
        pass

    return "/lessons/" + slug if slug in LessonLookup else None  # locale_id/lesson_slug


# no login_required as logged out users can view example/public workflows
@loads_workflow_for_read
def render_workflow(request: HttpRequest, workflow: Workflow):
    if (
        workflow.lesson_slug
        and _lesson_redirect_url(workflow.lesson_slug)
        and workflow.owner == request.user
    ):
        return redirect(_lesson_redirect_url(workflow.lesson_slug))
    else:
        if workflow.example and workflow.owner != request.user:
            workflow = _get_anonymous_workflow_for(workflow, request)

        modules = visible_modules(request)
        init_state = make_init_state(request, workflow=workflow, modules=modules)

        if any(
            step["last_relevant_delta_id"] != step["cached_render_result_delta_id"]
            for step in init_state["wfModules"].values()
        ):
            # We're returning a Workflow that may have stale WfModules. That's
            # fine, but are we _sure_ the renderer is about to render them?
            # Let's double-check. This will handle edge cases such as "we wiped
            # our caches" or maybe some bugs we haven't thought of.
            #
            # This isn't just for bug recovery. ChangeDataVersionCommand won't
            # queue_render until a client requests it.
            async_to_sync(rabbitmq.queue_render)(workflow.id, workflow.last_delta_id)

        return TemplateResponse(request, "workflow.html", {"initState": init_state})


# Retrieve or delete a workflow instance.
# Or reorder modules


class ApiDetail(View):
    @method_decorator(loads_workflow_for_write)
    def post(self, request: HttpRequest, workflow: Workflow):
        if request.content_type != "application/json":
            return HttpResponse(
                "request must have type application/json",
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            body = json.loads(request.body)
        except ValueError:
            return JsonResponse(
                {"message": "request is invalid JSON"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if (
            type(body) != dict
            or len(body) != 1
            or "public" not in body
            or type(body["public"]) != bool
        ):
            return JsonResponse(
                {
                    "message": 'request JSON must be an Object with a "public" property of type Boolean'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        workflow.public = body["public"]
        workflow.save(update_fields=["public"])
        return HttpResponse(status=status.HTTP_204_NO_CONTENT)

    @method_decorator(login_required)
    def delete(self, request: HttpRequest, workflow_id: int):
        try:
            with Workflow.authorized_lookup_and_cooperative_lock(
                "owner", request.user, request.session, pk=workflow_id
            ) as workflow_lock:
                workflow = workflow_lock.workflow
                workflow.delete()
            return HttpResponse(status=status.HTTP_204_NO_CONTENT)
        except Workflow.DoesNotExist as err:
            if err.args[0] == "owner access denied":
                return JsonResponse(
                    {"message": str(err), "status_code": 403},
                    status=status.HTTP_403_FORBIDDEN,
                )
            else:
                return JsonResponse(
                    {"message": "Workflow not found", "status_code": 404},
                    status=status.HTTP_404_NOT_FOUND,
                )


# Duplicate a workflow. Returns new wf as json in same format as wf list
class Duplicate(View):
    @method_decorator(loads_workflow_for_read)
    def post(self, request: HttpRequest, workflow: Workflow):
        workflow2 = workflow.duplicate(request.user)
        ctx = JsonizeContext(request.user, request.session, request.locale_id)
        json_dict = jsonize_clientside_workflow(
            workflow2.to_clientside(), ctx, is_init=True
        )

        server.utils.log_user_event_from_request(
            request, "Duplicate Workflow", {"name": workflow.name}
        )

        async_to_sync(rabbitmq.queue_render)(workflow2.id, workflow2.last_delta_id)

        return JsonResponse(json_dict, status=status.HTTP_201_CREATED)


class Report(View):
    """Render all the charts in a workflow."""

    @dataclass
    class WfModuleWithIframe:
        id: int
        delta_id: int

        @classmethod
        def from_wf_module(cls, wf_module: WfModule) -> Report.WfModuleWithIframe:
            return cls(id=wf_module.id, delta_id=wf_module.last_relevant_delta_id)

    @dataclass
    class TabWithIframes:
        slug: str
        name: str
        wf_modules: List[Report.WfModuleWithIframe]

        @classmethod
        def from_tab(
            cls, tab: Tab, module_zipfiles: Dict[str, ModuleZipfile]
        ) -> Report.TabWithIframes:
            all_wf_modules = tab.live_wf_modules.only(
                "id", "last_relevant_delta_id", "module_id_name"
            )

            wf_modules = [
                Report.WfModuleWithIframe.from_wf_module(wf_module)
                for wf_module in all_wf_modules
                if wf_module.module_id_name in module_zipfiles
                and wf_module.module_zipfile.get_optional_html() is not None
            ]
            return cls(slug=tab.slug, name=tab.name, wf_modules=wf_modules)

    @dataclass
    class ReportWorkflow:
        id: int
        name: str
        owner_name: str
        updated_at: datetime.datetime
        tabs: List[Report.TabWithIframes]

        @classmethod
        def from_workflow(cls, workflow: Workflow) -> Report.ReportWorkflow:
            module_zipfiles = MODULE_REGISTRY.all_latest()

            # prefetch would be nice, but it's tricky because A) we need to
            # filter out is_deleted; and B) we need to filter for modules that
            # have .html files.
            all_tabs = [
                Report.TabWithIframes.from_tab(tab, module_zipfiles)
                for tab in workflow.live_tabs
            ]
            tabs = [tab for tab in all_tabs if tab.wf_modules]
            return cls(
                id=workflow.id,
                name=workflow.name,
                owner_name=workbench_user_display(workflow.owner),
                updated_at=workflow.last_delta.datetime,
                tabs=tabs,
            )

    @method_decorator(loads_workflow_for_read)
    def get(self, request: HttpRequest, workflow: Workflow):
        report_workflow = Report.ReportWorkflow.from_workflow(workflow)
        return TemplateResponse(request, "report.html", {"workflow": report_workflow})
