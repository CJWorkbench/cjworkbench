from django.conf import settings
from django.conf.urls import url
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView
from django.urls import path
from . import views
from django.contrib.staticfiles import views as staticfiles_views
from .views import acl, lessons, oauth, workflows, uploads


def redirect(url: str):
    return RedirectView.as_view(url=url)


urlpatterns = [
    # ex: /
    #    url(r'^$', views.index, name='index'),
    url(r"^$", redirect("/workflows")),
    # list all workflows
    url(r"^workflows/$", workflows.Index.as_view(), name="workflows"),
    url(r"^lessons/?$", redirect("/lessons/en")),
    url(r"^lessons/(?P<locale_id>[a-z]+)$", lessons.render_lesson_list),
    url(r"^lessons/(?P<locale_id>[a-z]+)/$", redirect("/lessons/%(locale_id)s")),
    url(
        r"^lessons/(?P<locale_id>[a-z]+)/(?P<slug>[-a-z0-9]+)$",
        lessons.render_lesson_detail,
    ),
    url(
        r"^lessons/(?P<locale_id>[a-z]+)/(?P<slug>[-a-z0-9]+)/$",
        redirect("/lessons/%(locale_id)s/%(slug)s"),
    ),
    url(r"^courses/?$", redirect("/lessons/en")),
    url(r"^courses/(?P<locale_id>[a-z]+)/?$", redirect("/lessons/%(locale_id)s")),
    url(
        r"^courses/(?P<locale_id>[a-z]+)/(?P<course_slug>[-\w]+)$",
        lessons.render_course,
    ),
    url(
        r"^courses/(?P<locale_id>[a-z]+)/(?P<course_slug>[-\w]+)/$",
        redirect("/courses/%(course_slug)s"),
    ),
    url(
        r"^courses/(?P<locale_id>[a-z]+)/(?P<course_slug>[-\w]+)/(?P<lesson_slug>[-\w]+)$",
        lessons.render_course_lesson_detail,
    ),
    url(
        r"^courses/(?P<locale_id>[a-z]+)/(?P<course_slug>[-\w]+)/(?P<lesson_slug>[-\w]+)/$",
        redirect("/courses/%(course_slug)s/%(lesson_slug)s"),
    ),
    # workflows
    url(
        r"^workflows/(?P<workflow_id>[0-9]+)/$",
        workflows.render_workflow,
        name="workflow",
    ),
    # API
    path(
        "api/v1/workflows/<int:workflow_id>/steps/<slug:wf_module_slug>/uploads",
        uploads.UploadList.as_view(),
    ),
    path(
        "api/v1/workflows/<int:workflow_id>/steps/<slug:wf_module_slug>/uploads/<uuid:uuid>",
        uploads.Upload.as_view(),
    ),
    # Not-really-an-API API endpoints
    # TODO rename all these so they don't start with `/api`. (The only way to
    # use them is as a logged-in user.)
    url(r"^api/workflows/(?P<workflow_id>[0-9]+)/?$", workflows.workflow_detail),
    url(
        r"^api/workflows/(?P<workflow_id>[0-9]+)/duplicate/?$",
        workflows.Duplicate.as_view(),
    ),
    url(r"^workflows/(?P<workflow_id>[0-9]+)/report$", workflows.Report.as_view()),
    url(
        r"^api/workflows/(?P<workflow_id>[0-9]+)/acl/(?P<email>[0-9a-zA-Z-_@+.]+)$",
        acl.Entry.as_view(),
    ),
    url(r"^api/importfromgithub/?$", views.import_from_github),
    # WfModules (Modules applied in a workflow)
    url(
        r"^api/wfmodules/<int:wf_module_id>/tiles/v<int:delta_id>/r<int:tile_row>/c<int:tile_column>.json$",
        views.wfmodule_tile,
    ),
    # TODO: "render" and "output" are bad names. Differentiate them.
    path("api/wfmodules/<int:wf_module_id>/render", views.wfmodule_render),
    path("api/wfmodules/<int:wf_module_id>/output", views.wfmodule_output),
    path("api/wfmodules/<int:wf_module_id>/embeddata", views.wfmodule_embeddata),
    path("api/wfmodules/<int:wf_module_id>/value-counts", views.wfmodule_value_counts),
    path("public/moduledata/live/<int:wf_module_id>.csv", views.wfmodule_public_csv),
    path("public/moduledata/live/<int:wf_module_id>.json", views.wfmodule_public_json),
    # Parameters
    url(
        r"^oauth/create-secret/(?P<workflow_id>[0-9]+)/(?P<wf_module_id>[0-9]+)/(?P<param>[-_a-zA-Z0-9]+)/",
        oauth.start_authorize,
    ),
    url(r"^oauth/?$", oauth.finish_authorize),
    # Embeds
    url(r"^embed/(?P<wfmodule_id>[0-9]+)/?$", views.embed),
    # 404
    url(r"^404/$", TemplateView.as_view(template_name="404.html")),
    # 403
    url(r"^403/$", TemplateView.as_view(template_name="403.html")),
]

if settings.DEBUG:
    urlpatterns.append(url(r"^static/(?P<path>.*)$", staticfiles_views.serve))
