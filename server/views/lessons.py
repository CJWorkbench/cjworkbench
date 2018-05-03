from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.utils.translation import gettext as _
from django.template.response import TemplateResponse
from django.shortcuts import get_object_or_404, redirect
import json
from server.models import Lesson, Workflow
from server.serializers import LessonSerializer, UserSerializer
from server.views.workflows import make_init_state

# because get_object_or_404() is for _true_ django.db.models.Manager
def _get_lesson_or_404(slug):
    try:
        return Lesson.objects.get(slug)
    except Lesson.DoesNotExist:
        raise Http404(_('Lesson does not exist'))

def _render_post_lesson_detail(request, lesson):
    Workflow.objects.get_or_create(
        defaults={
            'name': _('Lesson: %(lesson_title)s') % { 'lesson_title': lesson.title },
            'public': False,
            'last_delta': None,
        },
        owner=request.user,
        lesson_slug=lesson.slug
    )

    return redirect(lesson) # so it's a GET


def _render_get_lesson_detail(request, lesson):
    workflow = get_object_or_404(Workflow, owner=request.user, lesson_slug=lesson.slug)

    init_state = make_init_state(request, workflow=workflow)
    init_state['lesson'] = LessonSerializer(lesson).data
    return TemplateResponse(request, 'workflow.html', { 'initState': json.dumps(init_state) })

@login_required
def render_lesson_detail(request, slug):
    lesson = _get_lesson_or_404(slug)

    if request.method == 'POST':
        # Create the Workflow if it doesn't exist, then redirect to GET
        return _render_post_lesson_detail(request, lesson)
    else:
        # Display the Workflow
        return _render_get_lesson_detail(request, lesson)

@login_required
def render_lesson_list(request):
    lessons = Lesson.objects.all()
    return TemplateResponse(request, 'lessons.html', {
        'initState': json.dumps({
            'loggedInUser': UserSerializer(request.user).data,
        }),
        'lessons': lessons,
    })
