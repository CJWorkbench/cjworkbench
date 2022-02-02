import json
from typing import Any, Dict, Optional

from asgiref.sync import async_to_sync
from django.conf import settings
from django.db import transaction
from django.http import Http404
from django.http.response import HttpResponseServerError
from django.shortcuts import redirect
from django.template.response import TemplateResponse

from cjwstate import rabbitmq
from cjwstate.models import Workflow
from cjwstate.models.dbutil import lock_user_by_id, query_clientside_user
from cjwstate.models.module_registry import MODULE_REGISTRY
from server.models.course import Course, CourseLookup, AllCoursesByLocale
from server.models.lesson import (
    Lesson,
    AllLessonsByLocale,
    LessonLookup,
    LessonSection,
    LessonSectionStep,
)
from server.serializers import jsonize_clientside_user
from server.views.workflows import visible_modules, make_init_state


def jsonize_step(step: LessonSectionStep) -> Dict[str, Any]:
    return {"html": step.html, "highlight": step.highlight, "testJs": step.test_js}


def jsonize_section(section: LessonSection) -> Dict[str, Any]:
    return {
        "title": section.title,
        "html": section.html,
        "steps": list(jsonize_step(step) for step in section.steps),
        "isFullScreen": section.is_full_screen,
    }


def jsonize_course(course: Course) -> Dict[str, Any]:
    return {"slug": course.slug, "title": course.title, "localeId": course.locale_id}


def jsonize_lesson(lesson: Lesson) -> Dict[str, Any]:
    return {
        "course": None if lesson.course is None else jsonize_course(lesson.course),
        "slug": lesson.slug,
        "localeId": lesson.locale_id,
        "header": {"title": lesson.header.title, "html": lesson.header.html},
        "sections": list(jsonize_section(section) for section in lesson.sections),
        "footer": {
            "title": lesson.footer.title,
            "html": lesson.footer.html,
            "isFullScreen": lesson.footer.is_full_screen,
        },
    }


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
            },
            owner=owner,
            anonymous_owner_session_key=session_key,
            lesson_slug=full_slug,
        )

        if created:
            _init_workflow_for_lesson(workflow, lesson)
        return workflow, created


def _init_workflow_for_lesson(workflow, lesson):
    # Create each step of each tab
    tab_dicts = lesson.initial_workflow.tabs
    for position, tab_dict in enumerate(tab_dicts):
        # Set selected module to last step in stack
        tab = workflow.tabs.create(
            position=position,
            slug=f"tab-{position + 1}",
            name=tab_dict["name"],
            selected_step_position=len(tab_dict["steps"]) - 1,
        )

        for order, step in enumerate(tab_dict["steps"]):
            _add_step_to_tab(step, order, tab, lesson)


def _add_step_to_tab(step_dict, order, tab, lesson):
    """
    Deserialize a Step from lesson initial_workflow.

    Raise `KeyError` if a module ID is invalid.
    """
    id_name = step_dict["module"]
    slug = step_dict["slug"]

    # 500 error if bad module id name
    module_zipfile = MODULE_REGISTRY.latest(id_name)  # raise KeyError, RuntimeError
    module_spec = module_zipfile.get_spec()

    # All params not set in json get default values
    # Also, we must have a dict with all param values set or we can't migrate
    # params later
    params = {**module_spec.param_schema.default, **step_dict["params"]}

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
    module_spec.param_schema.validate(params)  # raises ValueError

    return tab.steps.create(
        order=order,
        slug=slug,
        module_id_name=id_name,
        is_busy=module_spec.loads_data,  # assume we'll send a fetch
        params=params,
        is_collapsed=step_dict.get("collapsed", False),
        notes=step_dict.get("note", None),
    )


def _queue_workflow_updates(workflow: Workflow) -> None:
    have_a_module = False
    have_a_fetch_module = False

    for tab in workflow.tabs.all():
        for step in tab.steps.all():
            have_a_module = True
            # If this module fetches, do the fetch now (so e.g. Loadurl loads
            # immediately)
            if step.is_busy:
                have_a_fetch_module = True
                async_to_sync(rabbitmq.queue_fetch)(workflow.id, step.id)

    if have_a_module and not have_a_fetch_module:
        # Render. (e.g., pastecsv)
        async_to_sync(rabbitmq.queue_render)(workflow.id, workflow.last_delta_id)


def _render_get_lesson_detail(request, lesson):
    try:
        workflow, created = _ensure_workflow(request, lesson)
    except KeyError as err:
        return HttpResponseServerError(
            "initial_json asks for missing module: %s" % str(err)
        )
    except ValueError as err:
        return HttpResponseServerError("initial_json has invalid params: " + str(err))

    modules = visible_modules(request)

    init_state = make_init_state(request, workflow=workflow, modules=modules)
    init_state["lessonData"] = jsonize_lesson(lesson)

    # If we just initialized this workflow, start fetches and render
    if created:
        _queue_workflow_updates(workflow)
        if lesson.course:
            course_slug = lesson.course.slug
        else:
            course_slug = "None"

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
        with transaction.atomic():
            lock_user_by_id(request.user.id, for_write=False)
            logged_in_user = jsonize_clientside_user(
                query_clientside_user(request.user.id)
            )

    try:
        courses = AllCoursesByLocale[course.locale_id]
    except KeyError:
        courses = []

    # We render using HTML, not React, to make this page SEO-friendly.
    return TemplateResponse(
        request,
        "course.html",
        {
            "initState": json.dumps(
                {
                    "loggedInUser": logged_in_user,
                    "courses": [
                        dict(href=course.href, title=course.title)
                        for course in AllCoursesByLocale.get(request.locale_id, [])
                    ],
                }
            ),
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
        title="Workbench basics",
        locale_id=locale_id,
        lessons={lesson.slug: lesson for lesson in lessons},
    )
    return _render_course(request, course, "/lessons/%s" % locale_id)


# Even allowed for logged-out users
def render_course(request, locale_id, course_slug):
    course = _get_course_or_404(locale_id, course_slug)
    return _render_course(request, course, "/courses/%s/%s" % (locale_id, course.slug))
