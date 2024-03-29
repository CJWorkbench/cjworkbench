from __future__ import annotations

import datetime
import functools
import json
from http import HTTPStatus as status
from typing import Any, Callable, Dict, Optional, Tuple, Union

from asgiref.sync import async_to_sync
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.utils.decorators import method_decorator
from django.utils.cache import add_never_cache_headers
from django.views import View

from cjworkbench.i18n import default_locale
from cjworkbench.models.userprofile import UserProfile
from cjwstate import clientside, rabbitmq
from cjwstate.models.dbutil import (
    lock_user_by_id,
    query_user_usage,
    query_clientside_user,
    user_display_name,
)
from cjwstate.models import Step, Workflow
from cjwstate.models.fields import Role
from cjwstate.models.module_registry import MODULE_REGISTRY
from cjwstate.models.reports import build_report_for_workflow
from cjwstate.modules.types import ModuleZipfile
from server.models.course import CourseLookup
from server.models.lesson import LessonLookup
from server.serializers import (
    JsonizeContext,
    jsonize_clientside_init,
    jsonize_clientside_user,
    jsonize_clientside_workflow,
)


class Http302(Exception):
    def __init__(self, location: str):
        self.location = location


class WorkflowPermissionDenied(PermissionDenied):
    def __init__(self, workflow_path: str):
        super().__init__()
        self.workflow_path = workflow_path


def redirect_on_http302(status: int = status.OK):
    def decorator(func):
        @functools.wraps(func)
        def inner(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Http302 as err:
                return HttpResponseRedirect(err.location)

        return inner

    return decorator


def render_template_on_workflow_permission_denied(func):
    @functools.wraps(func)
    def inner(request, workflow_id_or_secret_id: Union[int, str], *args, **kwargs):
        try:
            return func(request, workflow_id_or_secret_id, *args, **kwargs)
        except WorkflowPermissionDenied as err:
            # report_path: set when the user has permission to access the report
            try:
                lookup_workflow_and_auth(
                    authorized_report_viewer, workflow_id_or_secret_id, request
                )
                report_path = err.workflow_path + "report"
            except WorkflowPermissionDenied:
                report_path = None
            return TemplateResponse(
                request,
                "workflow-403.html",
                dict(
                    user=request.user,
                    workflow_path=err.workflow_path,
                    report_path=report_path,
                ),
                status=status.FORBIDDEN,
            )

    return inner


def lookup_workflow_and_auth(
    auth: Callable[[Workflow, HttpRequest, bool], Tuple[bool, bool]],
    workflow_id_or_secret_id: Union[int, str],
    request: HttpRequest,
) -> Workflow:
    """Find a Workflow based on its id or secret_id.

    If workflow_id_or_secret_id is an int, search by id. Otherwise, search
    by secret_id.

    `auth(workflow, request, using_secret)` must return
    `(is_allowed, should_redirect_to_id)`.

    Raise Http404 if the Workflow does not exist.

    Raise WorkflowPermissionDenied if the workflow _does_ exist but the user
    does not have access.

    Raise Http302 if the user should send a near-identical request to the
    workflow's ID-based URL. (This implies callers must be wrapped in
    `@redirect_on_http302()`.)
    """
    if isinstance(workflow_id_or_secret_id, int):
        search = {"id": workflow_id_or_secret_id}
        using_secret = False
    else:
        search = {"secret_id": workflow_id_or_secret_id}
        using_secret = True

    workflow = get_object_or_404(Workflow, **search)

    allowed, want_redirect = auth(workflow, request, using_secret)

    if not allowed:
        raise WorkflowPermissionDenied(f"/workflows/{workflow_id_or_secret_id}/")

    if want_redirect:
        path = request.path.replace("%s" % workflow_id_or_secret_id, str(workflow.id))
        raise Http302(path)

    return workflow


def authorized_write(
    workflow: Workflow, request: HttpRequest, using_secret: bool
) -> bool:
    return Workflow.request_authorized_write(workflow, request), False


def authorized_read(
    workflow: Workflow, request: HttpRequest, using_secret: bool
) -> bool:
    user_allowed = Workflow.request_authorized_read(workflow, request)
    return (user_allowed or using_secret, user_allowed and using_secret)


def authorized_report_viewer(
    workflow: Workflow, request: HttpRequest, using_secret: bool
) -> bool:
    user_allowed = Workflow.request_authorized_report_viewer(workflow, request)
    return (user_allowed or using_secret, user_allowed and using_secret)


def _get_request_jsonize_context(
    request: HttpRequest, module_zipfiles: Dict[str, ModuleZipfile]
) -> JsonizeContext:
    return JsonizeContext(
        locale_id=request.locale_id,
        module_zipfiles=module_zipfiles,
    )


def make_init_state(
    request, workflow: Workflow, modules: Dict[str, ModuleZipfile]
) -> Dict[str, Any]:
    """Build a dict to embed as JSON in `window.initState` in HTML.

    Raise Http404 if the workflow disappeared.

    Side-effect: update workflow.last_viewed_at.
    """
    try:
        with workflow.cooperative_lock():  # raise DoesNotExist on race
            if request.user.is_anonymous:
                user = None
            else:
                lock_user_by_id(request.user.id, for_write=False)
                user = query_clientside_user(request.user.id)

            workflow.last_viewed_at = datetime.datetime.now()
            workflow.save(update_fields=["last_viewed_at"])

            state = clientside.Init(
                user=user,
                workflow=workflow.to_clientside(),
                tabs={tab.slug: tab.to_clientside() for tab in workflow.live_tabs},
                steps={
                    step.id: step.to_clientside(
                        force_module_zipfile=modules.get(step.module_id_name)
                    )
                    for step in Step.live_in_workflow(workflow).prefetch_related("tab")
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

    ctx = JsonizeContext(request.locale_id, modules)
    return jsonize_clientside_init(state, ctx)


def _render_workflows(request: HttpRequest, **kwargs) -> TemplateResponse:
    ctx = JsonizeContext(request.locale_id, {})

    workflows = list(
        Workflow.objects.filter(**kwargs)
        .filter(Q(lesson_slug__isnull=True) | Q(lesson_slug=""))
        .prefetch_related("acl", "owner")
        .order_by("-updated_at")
    )

    clientside_workflows = [
        w.to_clientside(include_tab_slugs=False, include_block_slugs=False)
        for w in workflows
    ]

    json_workflows = [
        jsonize_clientside_workflow(w, ctx, is_init=True) for w in clientside_workflows
    ]

    if request.user.is_anonymous:
        json_user = None
    else:
        with transaction.atomic():
            lock_user_by_id(request.user.id, for_write=False)
            json_user = jsonize_clientside_user(query_clientside_user(request.user.id))

    init_state = {
        "loggedInUser": json_user,
        "workflows": json_workflows,
    }

    return TemplateResponse(request, "workflows.html", {"initState": init_state})


class Index(View):
    @method_decorator(login_required)
    def post(self, request: HttpRequest):
        """Create a new workflow."""
        workflow = Workflow.create_and_init(
            name="Untitled Workflow", owner=request.user
        )
        return redirect("/workflows/%d/" % workflow.id)

    @method_decorator(login_required)
    def get(self, request: HttpRequest):
        return _render_workflows(request, owner=request.user)


@login_required
def shared_with_me(request: HttpRequest):
    return _render_workflows(request, acl__email=request.user.email)


# Not login_required: even guests can view examples
def examples(request: HttpRequest):
    return _render_workflows(request, in_all_users_workflow_lists=True)


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
@redirect_on_http302()
@render_template_on_workflow_permission_denied
def render_workflow(request: HttpRequest, workflow_id_or_secret_id: Union[int, str]):
    workflow = lookup_workflow_and_auth(
        authorized_read, workflow_id_or_secret_id, request
    )
    if (
        workflow.lesson_slug
        and _lesson_redirect_url(workflow.lesson_slug)
        and workflow.owner == request.user
    ):
        return redirect(_lesson_redirect_url(workflow.lesson_slug))
    else:
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
    @method_decorator(redirect_on_http302(status=status.TEMPORARY_REDIRECT))
    def post(self, request: HttpRequest, workflow_id: int):
        workflow = lookup_workflow_and_auth(authorized_write, workflow_id, request)
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
    @method_decorator(redirect_on_http302(status=status.TEMPORARY_REDIRECT))
    def delete(self, request: HttpRequest, workflow_id: int):
        try:
            with Workflow.authorized_lookup_and_cooperative_lock(
                "owner", request.user, request.session, pk=workflow_id
            ) as workflow:
                workflow.delete()

                if workflow.owner_id:
                    # We lock after delete, but it's still correct. DB commits
                    # are atomic: nothing is written yet.
                    lock_user_by_id(workflow.owner_id, for_write=True)
                    user_update = clientside.UserUpdate(
                        usage=query_user_usage(workflow.owner_id)
                    )
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

        if workflow.owner_id:
            async_to_sync(rabbitmq.send_user_update_to_user_clients)(
                workflow.owner_id, user_update
            )
        return HttpResponse(status=status.NO_CONTENT)


# Duplicate a workflow. Returns new wf as json in same format as wf list
class Duplicate(View):
    @method_decorator(redirect_on_http302(status=status.TEMPORARY_REDIRECT))
    def post(self, request: HttpRequest, workflow_id_or_secret_id: Union[int, str]):
        workflow = lookup_workflow_and_auth(
            authorized_read, workflow_id_or_secret_id, request
        )
        workflow2 = workflow.duplicate(request.user)
        ctx = JsonizeContext(request.locale_id, MODULE_REGISTRY.all_latest())
        json_dict = jsonize_clientside_workflow(
            workflow2.to_clientside(), ctx, is_init=True
        )

        async_to_sync(rabbitmq.queue_render)(workflow2.id, workflow2.last_delta_id)

        return JsonResponse(json_dict, status=status.CREATED)


class Report(View):
    """Render all the charts in a workflow."""

    @method_decorator(redirect_on_http302(status=status.TEMPORARY_REDIRECT))
    def get(self, request: HttpRequest, workflow_id_or_secret_id: Union[int, str]):
        workflow = lookup_workflow_and_auth(
            authorized_report_viewer, workflow_id_or_secret_id, request
        )
        assert request.path_info.endswith("/report")
        workflow_path = request.path_info[: -len("/report")]
        init_state = make_init_state(request, workflow=workflow, modules={})
        blocks = build_report_for_workflow(workflow)
        if (
            not workflow.public
            and not request.user.is_anonymous
            and workflow.acl.filter(
                email=request.user.email, role=Role.REPORT_VIEWER
            ).exists()
        ):
            can_view_workflow = False
        else:
            can_view_workflow = True
        response = TemplateResponse(
            request,
            "report.html",
            {
                "initState": init_state,
                "workflow": workflow,
                "workflow_path": workflow_path,
                "blocks": blocks,
                "owner_name": user_display_name(workflow.owner),
                "can_view_workflow": can_view_workflow,
            },
        )
        add_never_cache_headers(response)
        return response
