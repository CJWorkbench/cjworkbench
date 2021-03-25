from __future__ import annotations

import datetime
import functools
import json
from http import HTTPStatus as status
from typing import Any, Callable, Dict, List, Optional

from asgiref.sync import async_to_sync
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
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
from django.views import View

import server.utils
from cjworkbench.i18n import default_locale
from cjworkbench.models.userprofile import UserProfile
from cjwstate import clientside, rabbitmq
from cjwstate.models import Step, Tab, Workflow
from cjwstate.models.module_registry import MODULE_REGISTRY
from cjwstate.models.reports import build_report_for_workflow
from cjwstate.modules.types import ModuleZipfile
from server.models.course import CourseLookup
from server.models.lesson import LessonLookup
from server.serializers import (
    JsonizeContext,
    jsonize_clientside_init,
    jsonize_clientside_workflow,
    jsonize_user,
)
from server.settingsutils import workbench_user_display


class Http302(Exception):
    def __init__(self, location: str):
        self.location = location


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

    Raise Http404 if the Workflow does not exist and PermissionDenied if the
    workflow _does_ exist but the user does not have access.

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
        raise PermissionDenied()

    if want_redirect:
        raise Http302("/workflows/%d/" % workflow.id)

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
    # Anonymous has no user_profile
    user_profile = UserProfile.objects.filter(user_id=request.user.id).first()
    return JsonizeContext(
        user=request.user,
        user_profile=user_profile,
        session=request.session,
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

    ctx = _get_request_jsonize_context(request, modules)
    return jsonize_clientside_init(state, ctx)


def _render_workflows(request: HttpRequest, **kwargs) -> TemplateResponse:
    ctx = _get_request_jsonize_context(request, {})

    workflows = (
        Workflow.objects.filter(**kwargs)
        .filter(Q(lesson_slug__isnull=True) | Q(lesson_slug=""))
        .prefetch_related("acl", "owner")
        .order_by("-updated_at")
    )
    json_workflows = [
        jsonize_clientside_workflow(
            w.to_clientside(include_tab_slugs=False, include_block_slugs=False),
            ctx,
            is_init=True,
        )
        for w in workflows
    ]

    init_state = {
        "loggedInUser": (
            None
            if request.user.is_anonymous
            else jsonize_user(request.user, ctx.user_profile)
        ),
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


# Not login_required: even guests can view recipes
def examples(request: HttpRequest):
    return _render_workflows(request, in_all_users_workflow_lists=True)


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
@redirect_on_http302()
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
    @method_decorator(redirect_on_http302(status=status.TEMPORARY_REDIRECT))
    def post(self, request: HttpRequest, workflow_id_or_secret_id: Union[int, str]):
        workflow = lookup_workflow_and_auth(
            authorized_read, workflow_id_or_secret_id, request
        )
        workflow2 = workflow.duplicate(request.user)
        ctx = _get_request_jsonize_context(request, MODULE_REGISTRY.all_latest())
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

    @method_decorator(redirect_on_http302(status=status.TEMPORARY_REDIRECT))
    def get(self, request: HttpRequest, workflow_id_or_secret_id: Union[int, str]):
        workflow = lookup_workflow_and_auth(
            authorized_report_viewer, workflow_id_or_secret_id, request
        )
        init_state = make_init_state(request, workflow=workflow, modules={})
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
