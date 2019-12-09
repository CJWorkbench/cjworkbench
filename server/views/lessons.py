import json
from typing import Optional
from asgiref.sync import async_to_sync
from django.conf import settings
from django.db import transaction
from django.http import Http404
from django.http.response import HttpResponseServerError
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from server import rabbitmq
import server.utils
from cjwstate.models.commands import InitWorkflowCommand
from cjwstate.models import Workflow, ModuleVersion
from server.models.course import Course, CourseLookup, AllCoursesByLocale
from server.models.lesson import Lesson, AllLessonsByLocale, LessonLookup
from server.serializers import LessonSerializer, UserSerializer
from server.views.workflows import visible_modules, make_init_state


def _get_course_or_404(locale_id, slug):
    try:
        return CourseLookup[locale_id + "/" + slug]
    except KeyError:
        raise Http404("Course does not exist")


def _get_lesson_or_404(locale_id: str, course_slug: Optional[str], lesson_slug: str):
    """
    Return Lesson or raise Http404.
    """
    try:
        if course_slug is None:
            return LessonLookup[locale_id + "/" + lesson_slug]
        else:
            course = _get_course_or_404(locale_id, course_slug)  # raises Http404
            return course.lessons[lesson_slug]
    except KeyError:
        raise Http404("Course does not contain lesson")


def _ensure_workflow(request, lesson: Lesson):
    if request.user.is_authenticated:
        owner = request.user
        session_key = None
    else:
        owner = None
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key

    # full_slug: 'intro-to-data-journalism/group' (it's in a course) or
    # 'scrape-table' (course=None)
    if lesson.course is None:
        full_slug = lesson.slug
    else:
        full_slug = "/".join((lesson.course.slug, lesson.slug))

    with transaction.atomic():
        workflow, created = Workflow.objects.get_or_create(
            defaults={
                "name": "Lesson: "
                + lesson.title,  # https://www.pivotaltracker.com/story/show/168752481
                "public": False,
                "last_delta": None,
            },
            owner=owner,
            anonymous_owner_session_key=session_key,
            lesson_slug=full_slug,
        )

        if created:
            _init_workflow_for_lesson(workflow, lesson)
        return workflow, created


def _init_workflow_for_lesson(workflow, lesson):
    InitWorkflowCommand.create(workflow)

    # Create each wfModule of each tab
    tab_dicts = lesson.initial_workflow.tabs
    for position, tab_dict in enumerate(tab_dicts):
        # Set selected module to last wfmodule in stack
        tab = workflow.tabs.create(
            position=position,
            slug=f"tab-{position + 1}",
            name=tab_dict["name"],
            selected_wf_module_position=len(tab_dict["wfModules"]) - 1,
        )

        for order, wfm in enumerate(tab_dict["wfModules"]):
            _add_wf_module_to_tab(wfm, order, tab, workflow.last_delta_id, lesson)


def _add_wf_module_to_tab(wfm_dict, order, tab, delta_id, lesson):
    """
    Deserialize a WfModule from lesson initial_workflow
    """
    id_name = wfm_dict["module"]
    slug = wfm_dict["slug"]

    # 500 error if bad module id name
    module_version = ModuleVersion.objects.latest(id_name)

    # All params not set in json get default values
    # Also, we must have a dict with all param values set or we can't migrate
    # params later
    params = {**module_version.default_params, **wfm_dict["params"]}

    # Rewrite 'url' params: if the spec has them as relative, make them the
    # absolute path -- relative to the lesson URL.
    if "url" in params:
        if params["url"].startswith("./"):
            params["url"] = "".join(
                [
                    settings.STATIC_URL,
                    ("lessons/" if lesson.course is None else "courses/"),
                    f"{lesson.locale_id}/",
                    (
                        lesson.slug
                        if lesson.course is None
                        else f"{lesson.course.slug}/{lesson.slug}"
                    ),
                    params["url"][1:],  # include the '/'
                ]
            )

    # 500 error if params are invalid
    # TODO testme
    module_version.param_schema.validate(params)  # raises ValueError

    return tab.wf_modules.create(
        order=order,
        slug=slug,
        module_id_name=id_name,
        is_busy=module_version.loads_data,  # assume we'll send a fetch
        last_relevant_delta_id=delta_id,
        params=params,
        is_collapsed=wfm_dict.get("collapsed", False),
        notes=wfm_dict.get("note", None),
    )


def _queue_workflow_updates(workflow: Workflow) -> None:
    have_a_module = False
    have_a_fetch_module = False

    for tab in workflow.tabs.all():
        for wfm in tab.wf_modules.all():
            have_a_module = True
            # If this module fetches, do the fetch now (so e.g. Loadurl loads
            # immediately)
            if wfm.is_busy:
                have_a_fetch_module = True
                async_to_sync(rabbitmq.queue_fetch)(workflow.id, wfm.id)

    if have_a_module and not have_a_fetch_module:
        # Render. (e.g., pastecsv)
        async_to_sync(rabbitmq.queue_render)(workflow.id, workflow.last_delta_id)


def _render_get_lesson_detail(request, lesson):
    try:
        workflow, created = _ensure_workflow(request, lesson)
    except ModuleVersion.DoesNotExist:
        return HttpResponseServerError("initial_json asks for missing module")
    except ValueError as err:
        return HttpResponseServerError("initial_json has invalid params: " + str(err))

    modules = visible_modules(request)

    init_state = make_init_state(request, workflow=workflow, modules=modules)
    init_state["lessonData"] = LessonSerializer(lesson).data

    # If we just initialized this workflow, start fetches and render
    if created:
        _queue_workflow_updates(workflow)
        if lesson.course:
            course_slug = lesson.course.slug
        else:
            course_slug = "None"
        server.utils.log_user_event_from_request(
            request, "Start lesson in course %s" % (course_slug)
        )

    return TemplateResponse(request, "workflow.html", {"initState": init_state})


# Even allowed for logged-out users
def render_course_lesson_detail(request, locale_id, course_slug, lesson_slug):
    lesson = _get_lesson_or_404(locale_id, course_slug, lesson_slug)
    return _render_get_lesson_detail(request, lesson)


# Even allowed for logged-out users
def render_lesson_detail(request, locale_id, slug):
    lesson = _get_lesson_or_404(locale_id, None, slug)
    return _render_get_lesson_detail(request, lesson)


def _render_course(request, course, lesson_url_prefix):
    logged_in_user = None
    if request.user and request.user.is_authenticated:
        logged_in_user = UserSerializer(request.user).data

    try:
        courses = AllCoursesByLocale[course.locale_id]
    except KeyError:
        courses = []

    # We render using HTML, not React, to make this page SEO-friendly.
    return TemplateResponse(
        request,
        "course.html",
        {
            "initState": json.dumps({"loggedInUser": logged_in_user}),
            "course": course,
            "courses": courses,
            "lessons": list(course.lessons.values()),
            "lesson_url_prefix": lesson_url_prefix,
        },
    )


# Even allowed for logged-out users
def render_lesson_list(request, locale_id):
    # Make a "fake" Course to encompass Lessons
    #
    # Do not build this Course using LessonLookup: LessonLookup contains
    # "hidden" lessons; AllLessonsByLocale does not.
    locale_id = locale_id or request.locale_id
    try:
        lessons = AllLessonsByLocale[locale_id]
    except KeyError:
        return redirect("/lessons/en")
    course = Course(
        title="Lessons",
        locale_id=locale_id,
        lessons={lesson.slug: lesson for lesson in lessons},
    )
    return _render_course(request, course, "/lessons/%s" % locale_id)


# Even allowed for logged-out users
def render_course(request, locale_id, course_slug):
    course = _get_course_or_404(locale_id, course_slug)
    return _render_course(request, course, "/courses/%s/%s" % (locale_id, course.slug))
