from django.http import Http404
from django.db import transaction
from django.template.response import TemplateResponse
from django.utils.translation import gettext as _
from django.shortcuts import redirect
import json
from server.models.commands import InitWorkflowCommand
from server.models import Lesson, Module, Workflow
from server.serializers import LessonSerializer, UserSerializer
from server.views.workflows import make_init_state


# because get_object_or_404() is for _true_ django.db.models.Manager
def _get_lesson_or_404(slug):
    try:
        return Lesson.objects.get(slug)
    except Lesson.DoesNotExist:
        raise Http404(_('Lesson does not exist'))


def _ensure_workflow(request, lesson):
    if request.user.is_authenticated:
        owner = request.user
        session_key = None
    else:
        owner = None
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key

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
            lesson_slug=lesson.slug
        )
        if created:
            workflow.tabs.create(position=0)
            InitWorkflowCommand.create(workflow)
        return workflow


def _render_get_lesson_detail(request, lesson):
    workflow = _ensure_workflow(request, lesson)
    modules = Module.objects.all()

    init_state = make_init_state(request, workflow=workflow, modules=modules)
    init_state['lessonData'] = LessonSerializer(lesson).data
    return TemplateResponse(request, 'workflow.html',
                            {'initState': init_state})


# Even allowed for logged-out users
def render_lesson_detail(request, slug):
    lesson = _get_lesson_or_404(slug)

    if request.method == 'POST':
        # GET already creates the workflow (#160041704), so let's just
        # redirect to it.
        return redirect(lesson)
    else:
        # Display the Workflow
        return _render_get_lesson_detail(request, lesson)


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
