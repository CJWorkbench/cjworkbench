from __future__ import annotations

import datetime
import json
from dataclasses import dataclass
from http import HTTPStatus as status
from typing import Any, Dict, List, Optional

from asgiref.sync import async_to_sync
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Q
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils.decorators import method_decorator
from django.views import View

from cjwstate import clientside, rabbitmq
from cjwstate.models import Workflow, Step, Tab
from cjwstate.models.module_registry import MODULE_REGISTRY
from cjwstate.modules.types import ModuleZipfile
from cjwstate.models.reports import build_report_for_workflow
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
    """Build a dict to embed as JSON in `window.initState` in HTML.

    Raise Http404 if the workflow disappeared.

    Side-effect: update workflow.last_viewed_at.
    """
    try:
        with workflow.cooperative_lock():  # raise DoesNotExist on race
            workflow.last_viewed_at = datetime.datetime.now()
            workflow.save(update_fields=["last_viewed_at"])

            state = clientside.Init(
                workflow=workflow.to_clientside(),
                tabs={tab.slug: tab.to_clientside() for tab in workflow.live_tabs},
                steps={
                    step.id: step.to_clientside()
                    for step in Step.live_in_workflow(workflow)
                },
                modules={
                    module_id: clientside.Module(
                        spec=module.get_spec(),
                        js_module=module.get_optional_js_module(),
                    )
                    for module_id, module in modules.items()
                },
                blocks={
                    block.slug: block.to_clientside() for block in workflow.blocks.all()
                },
                settings={
                    "bigTableRowsPerTile": settings.BIG_TABLE_ROWS_PER_TILE,
                    "bigTableColumnsPerTile": settings.BIG_TABLE_COLUMNS_PER_TILE,
                },
            )
    except Workflow.DoesNotExist:
        raise Http404("Workflow was recently deleted")

    ctx = JsonizeContext(request.user, request.session, request.locale_id, modules)
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

        ctx = JsonizeContext(request.user, request.session, request.locale_id, {})

        def list_workflows_as_json(**kwargs) -> List[Dict[str, Any]]:
            workflows = (
                Workflow.objects.filter(**kwargs)
                .prefetch_related("acl", "owner")
                .order_by("-updated_at")
                .filter(Q(lesson_slug__isnull=True) | Q(lesson_slug=""))
            )
            return [
                jsonize_clientside_workflow(
                    w.to_clientside(include_tab_slugs=False, include_block_slugs=False),
                    ctx,
                    is_init=True,
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
    """If not owner, return a cached duplicate of `workflow`.

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
        except IntegrityError:
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
    """Load all ModuleZipfiles the user may use."""
    ret = dict(MODULE_REGISTRY.all_latest())  # shallow copy

    if not request.user.is_authenticated and "pythoncode" in ret:
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
            for step in init_state["steps"].values()
        ):
            # We're returning a Workflow that may have stale Steps. That's
            # fine, but are we _sure_ the renderer is about to render them?
            # Let's double-check. This will handle edge cases such as "we wiped
            # our caches" or maybe some bugs we haven't thought of.
            #
            # This isn't just for bug recovery. SetStepDataVersion won't
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
                status=status.BAD_REQUEST,
            )
        try:
            body = json.loads(request.body)
        except ValueError:
            return JsonResponse(
                {"message": "request is invalid JSON"},
                status=status.BAD_REQUEST,
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
                status=status.BAD_REQUEST,
            )
        workflow.public = body["public"]
        workflow.save(update_fields=["public"])
        return HttpResponse(status=status.NO_CONTENT)

    @method_decorator(login_required)
    def delete(self, request: HttpRequest, workflow_id: int):
        try:
            with Workflow.authorized_lookup_and_cooperative_lock(
                "owner", request.user, request.session, pk=workflow_id
            ) as workflow_lock:
                workflow = workflow_lock.workflow
                workflow.delete()
            return HttpResponse(status=status.NO_CONTENT)
        except Workflow.DoesNotExist as err:
            if err.args[0] == "owner access denied":
                return JsonResponse(
                    {"message": str(err), "status_code": 403},
                    status=status.FORBIDDEN,
                )
            else:
                return JsonResponse(
                    {"message": "Workflow not found", "status_code": 404},
                    status=status.NOT_FOUND,
                )


# Duplicate a workflow. Returns new wf as json in same format as wf list
class Duplicate(View):
    @method_decorator(loads_workflow_for_read)
    def post(self, request: HttpRequest, workflow: Workflow):
        workflow2 = workflow.duplicate(request.user)
        ctx = JsonizeContext(
            request.user,
            request.session,
            request.locale_id,
            dict(MODULE_REGISTRY.all_latest()),
        )
        json_dict = jsonize_clientside_workflow(
            workflow2.to_clientside(), ctx, is_init=True
        )

        server.utils.log_user_event_from_request(
            request, "Duplicate Workflow", {"name": workflow.name}
        )

        async_to_sync(rabbitmq.queue_render)(workflow2.id, workflow2.last_delta_id)

        return JsonResponse(json_dict, status=status.CREATED)


class Report(View):
    """Render all the charts in a workflow."""

    @method_decorator(loads_workflow_for_read)
    def get(self, request: HttpRequest, workflow: Workflow):
        modules = visible_modules(request)
        init_state = make_init_state(request, workflow=workflow, modules=modules)
        blocks = build_report_for_workflow(workflow)
        return TemplateResponse(
            request,
            "report.html",
            {
                "initState": init_state,
                "workflow": workflow,
                "blocks": blocks,
                "owner_name": workbench_user_display(workflow.owner),
            },
        )
