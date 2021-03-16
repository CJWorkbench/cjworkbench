from django.conf import settings
from django.conf.urls import url
from django.contrib.staticfiles import views as staticfiles_views
from django.urls import include, path
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView

import server.views.jsdata.timezones

from .views import (
    acl,
    files,
    health,
    importfromgithub,
    jsdata,
    lessons,
    # modules,
    oauth,
    steps,
    tusd_hooks,
    workflows,
)


def redirect(url: str):
    return RedirectView.as_view(url=url)


urlpatterns = [
    # ex: /
    #    url(r'^$', views.index, name='index'),
    url(r"^$", redirect("/workflows")),
    url(r"^workflows/$", redirect("/workflows")),
    # list all workflows
    url(r"^workflows$", workflows.Index.as_view()),
    url(r"^workflows/shared-with-me$", workflows.shared_with_me),
    url(r"^workflows/examples$", workflows.examples),
    # lessons and courses
    url(r"^lessons/(?P<locale_id>[a-z]{2})$", lessons.render_lesson_list),
    url(r"^lessons/(?P<locale_id>[a-z]{2})/$", redirect("/lessons/%(locale_id)s")),
    url(
        r"^lessons/(?P<locale_id>[a-z]{2})/(?P<slug>[-a-z0-9]+)$",
        lessons.render_lesson_detail,
    ),
    url(
        r"^lessons/(?P<locale_id>[a-z]{2})/(?P<slug>[-a-z0-9]+)/$",
        redirect("/lessons/%(locale_id)s/%(slug)s"),
    ),
    url(r"^courses/(?P<locale_id>[a-z]{2})/?$", redirect("/lessons/%(locale_id)s")),
    url(
        r"^courses/(?P<locale_id>[a-z]{2})/(?P<course_slug>[-\w]+)$",
        lessons.render_course,
    ),
    url(
        r"^courses/(?P<locale_id>[a-z]{2})/(?P<course_slug>[-\w]+)/$",
        redirect("/courses/%(course_slug)s"),
    ),
    url(
        r"^courses/(?P<locale_id>[a-z]{2})/(?P<course_slug>[-\w]+)/(?P<lesson_slug>[-\w]+)$",
        lessons.render_course_lesson_detail,
    ),
    url(
        r"^courses/(?P<locale_id>[a-z]{2})/(?P<course_slug>[-\w]+)/(?P<lesson_slug>[-\w]+)/$",
        redirect("/courses/%(course_slug)s/%(lesson_slug)s"),
    ),
    # backwards-compat URLs: /courses/intro-to-data-journalism, /lessons/scrape-using-xpath
    url(r"^courses/?$", redirect("/lessons/en")),
    url(
        r"^courses/(?P<course_slug>[-\w]+)/?$", redirect("/courses/en/%(course_slug)s")
    ),
    url(
        r"^courses/(?P<course_slug>[-\w]+)/(?P<lesson_slug>[-\w]+)/?$",
        redirect("/courses/en/%(course_slug)s/%(lesson_slug)s"),
    ),
    url(r"^lessons/?$", redirect("/lessons/en")),
    url(
        r"^lessons/(?P<lesson_slug>[-\w]+)/?$", redirect("/lessons/en/%(lesson_slug)s")
    ),
    # workflows
    url(
        r"^workflows/(?P<workflow_id>[0-9]+)/$",
        workflows.render_workflow,
        name="workflow",
    ),
    # API
    path(
        "api/v1/workflows/<int:workflow_id>/steps/<slug:step_slug>/files",
        files.create_tus_upload_for_workflow_and_step,
    ),
    path("tusd-hooks", tusd_hooks.tusd_hooks),  # haproxy blocks this one
    # Not-really-an-API API endpoints
    # TODO rename all these so they don't start with `/api`. (The only way to
    # use them is as a logged-in user.)
    url(r"^api/workflows/(?P<workflow_id>[0-9]+)/?$", workflows.ApiDetail.as_view()),
    url(
        r"^api/workflows/(?P<workflow_id>[0-9]+)/duplicate/?$",
        workflows.Duplicate.as_view(),
    ),
    url(
        r"^api/workflows/(?P<workflow_id>[0-9]+)/acl/(?P<email>[0-9a-zA-Z-_@+.]+)$",
        acl.Entry.as_view(),
    ),
    url(r"^api/importfromgithub/?$", importfromgithub.import_from_github),
    # Decent URLs
    path(
        "workflows/<int:workflow_id>/",
        include(
            [
                path("report", workflows.Report.as_view()),
                # path("steps/<slug:step_slug>/", include([
                #     path("delta-<int:delta_id>/", include([
                #         path("result-json.json", steps.result_json),
                #         path("result-table-slice.json", steps.result_table_slice),
                #         path("result-table.csv", steps.result_table_csv),
                #         path("result-table.json", steps.result_table_json),
                #     ]))
                # ])),
                path(
                    "tiles/<slug:step_slug>/delta-<int:delta_id>/<int:tile_row>,<int:tile_column>.json",
                    steps.tile,
                ),
            ]
        ),
    ),
    # path(
    #     "modules/<slug:module_slug>.html",
    #     modules.module_html,
    # ),
    # Steps -- deprecated URLs
    #
    # The "output" and "public_csv"/"public_json" URLs are widely used online.
    # We stopped publishing them [2021-03-17]. TODO migrate our users away from
    # them.
    path("api/wfmodules/<int:step_id>/render", steps.deprecated_render),  # DELETEME
    path("api/wfmodules/<int:step_id>/output", steps.deprecated_output),
    path(
        "api/wfmodules/<int:step_id>/embeddata", steps.deprecated_embeddata
    ),  # DELETEME
    path(
        "api/wfmodules/<int:step_id>/value-counts", steps.deprecated_value_counts
    ),  # DELETEME
    path("public/moduledata/live/<int:step_id>.csv", steps.deprecated_public_csv),
    path("public/moduledata/live/<int:step_id>.json", steps.deprecated_public_json),
    url(r"^embed/(?P<step_id>[0-9]+)/?$", steps.deprecated_embed),
    # Parameters
    url(
        r"^oauth/create-secret/(?P<workflow_id>[0-9]+)/(?P<step_id>[0-9]+)/(?P<param>[-_a-zA-Z0-9]+)/",
        oauth.start_authorize,
    ),
    url(r"^oauth/?$", oauth.finish_authorize),
    # 404, 403, status
    url(r"^404/$", TemplateView.as_view(template_name="404.html")),
    url(r"^403/$", TemplateView.as_view(template_name="403.html")),
    url(r"^healthz$", health.healthz),
    # JavaScript support data
    path("jsdata/timezones.json", jsdata.timezones.index),
]

if settings.DEBUG:
    urlpatterns.append(url(r"^static/(?P<path>.*)$", staticfiles_views.serve))
