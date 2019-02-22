import json
from asgiref.sync import async_to_sync
from django.db import transaction
from django.http import Http404
from django.http.response import HttpResponseServerError
from django.template.response import TemplateResponse
from django.utils.translation import gettext as _
from server import rabbitmq
from server.models.commands import InitWorkflowCommand
from server.models import Workflow, ModuleVersion
from server.models.course import Course, CourseLookup
from server.models.lesson import Lesson
from server.serializers import LessonSerializer, UserSerializer
from server.views.workflows import visible_modules, make_init_state


# because get_object_or_404() is for _true_ django.db.models.Manager
def _get_lesson_or_404(slug):
    try:
        return Lesson.objects.get(slug)
    except Lesson.DoesNotExist:
        raise Http404(_('Lesson does not exist'))


def _get_course_and_lesson_or_404(course_slug, lesson_slug) -> Course:
    """
    Return (Course, Lesson) or raise Http404.
    """

    try:
        course = CourseLookup[course_slug]
    except KeyError:
        raise Http404('Course does not exist')

    lesson = course.find_lesson_by_slug(lesson_slug)
    if not lesson:
        raise Http404('Course does not contain lesson')
    return course, lesson


def _ensure_workflow(request, course: Course, lesson: Lesson):
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
    if course is None:
        full_slug = lesson.slug
    else:
        full_slug = '/'.join((course.slug, lesson.slug))

    with transaction.atomic():
        workflow, created = Workflow.objects.get_or_create(
            defaults={
                'name': _('Lesson: %(lesson_title)s') % {
                    'lesson_title': lesson.title
                },
                'public': False,
                'last_delta': None,
            },
            owner=owner,
            anonymous_owner_session_key=session_key,
            lesson_slug=full_slug
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
            slug=f'tab-{position + 1}',
            name=tab_dict['name'],
            selected_wf_module_position=len(tab_dict['wfModules']) - 1
        )

        for order, wfm in enumerate(tab_dict['wfModules']):
            _add_wf_module_to_tab(wfm, order, tab, workflow.last_delta_id)


def _add_wf_module_to_tab(wfm_dict, order, tab, delta_id):
    """
    Deserialize a WfModule from lesson initial_workflow
    """
    id_name = wfm_dict['module']

    # 500 error if bad module id name
    module_version = ModuleVersion.objects.latest(id_name)

    # All params not set in json get default values
    # Also, we must have a dict with all param values set or we can't migrate
    # params later
    params = {
        **module_version.default_params,
        **wfm_dict['params'],
    }

    # 500 error if params are invalid
    # TODO testme
    module_version.param_schema.validate(params)  # raises ValueError

    return tab.wf_modules.create(
        order=order,
        module_id_name=id_name,
        is_busy=module_version.loads_data,  # assume we'll send a fetch
        last_relevant_delta_id=delta_id,
        params=params
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
                async_to_sync(rabbitmq.queue_fetch)(wfm)

    if have_a_module and not have_a_fetch_module:
        # Render. (e.g., pastecsv)
        async_to_sync(rabbitmq.queue_render)(workflow.id,
                                             workflow.last_delta_id)


def _render_get_lesson_detail(request, course, lesson):
    try:
        workflow, created = _ensure_workflow(request, course, lesson)
    except ModuleVersion.DoesNotExist:
        return HttpResponseServerError('initial_json asks for missing module')
    except ValueError as err:
        return HttpResponseServerError('initial_json has invalid params: '
                                       + str(err))

    modules = visible_modules(request)

    init_state = make_init_state(request, workflow=workflow, modules=modules)
    init_state['lessonData'] = LessonSerializer(lesson).data

    # If we just initialized this workflow, start fetches and render
    if created:
        _queue_workflow_updates(workflow)

    return TemplateResponse(request, 'workflow.html',
                            {'initState': init_state})


# Even allowed for logged-out users
def render_course_lesson_detail(request, course_slug, lesson_slug):
    course, lesson = _get_course_and_lesson_or_404(course_slug, lesson_slug)
    return _render_get_lesson_detail(request, course, lesson)


# Even allowed for logged-out users
def render_lesson_detail(request, slug):
    lesson = _get_lesson_or_404(slug)
    return _render_get_lesson_detail(request, None, lesson)


# Even allowed for logged-out users
def render_lesson_list(request):
    lessons = Lesson.objects.all()
    logged_in_user = None
    if request.user and request.user.is_authenticated:
        logged_in_user = UserSerializer(request.user).data

    return TemplateResponse(request, 'lessons.html', {
        'initState': json.dumps({
            'loggedInUser': logged_in_user,
        }),
        'lessons': lessons,
    })
