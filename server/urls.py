from django.conf.urls import url
from django.urls import include, path, register_converter
from django.views.generic.base import RedirectView

import server.views.jsdata.timezones

from .converters import WorkflowIdOrSecretIdConverter
from .views import (
    acl,
    files,
    health,
    importfromgithub,
    jsdata,
    lessons,
    manifest,
    modules,
    oauth,
    steps,
    workflows,
)

register_converter(WorkflowIdOrSecretIdConverter, "workflow_id_or_secret_id")


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
    path(
        "workflows/<workflow_id_or_secret_id:workflow_id_or_secret_id>/",
        workflows.render_workflow,
        name="workflow",
    ),
    # API
    path(
        "api/v1/workflows/<int:workflow_id>/steps/<slug:step_slug>/files",
        files.create_tus_upload_for_workflow_and_step,
    ),
    # Not-really-an-API API endpoints
    # TODO rename all these so they don't start with `/api`. (The only way to
    # use them is as a logged-in user.)
    path("api/workflows/<int:workflow_id>", workflows.ApiDetail.as_view()),
    path("api/workflows/<int:workflow_id>/", workflows.ApiDetail.as_view()),  # TODO nix
    path("api/workflows/<int:workflow_id>/acl/<str:email>", acl.Entry.as_view()),
    url(r"^api/importfromgithub/?$", importfromgithub.import_from_github),
    # Decent URLs
    path(
        "workflows/<workflow_id_or_secret_id:workflow_id_or_secret_id>/",
        include(
            [
                path("duplicate", workflows.Duplicate.as_view()),
                path("report", workflows.Report.as_view()),
                path("api", workflows.ApiInstructions.as_view()),
                path(
                    "steps/<slug:step_slug>/",
                    include(
                        [
                            path(
                                "delta-<int:delta_id>/result-json.json",
                                steps.result_json,
                            ),
                            path(
                                "current-result-table.csv",
                                steps.current_result_table_csv,
                            ),
                            path(
                                "current-result-table.json",
                                steps.current_result_table_json,
                            ),
                        ],
                    ),
                ),
                path(
                    "tiles/<slug:step_slug>/delta-<int:delta_id>/<int:tile_row>,<int:tile_column>.json",
                    steps.tile,
                ),
            ]
        ),
    ),
    path(
        # URLs you can't access by workflow secret_id (comments explain why)
        "workflows/<int:workflow_id>/",
        include(
            [
                path("acl", acl.Index.as_view()),
                path("acl/<str:email>", acl.Entry.as_view()),
                path(
                    "steps/<slug:step_slug>/",
                    include(
                        [
                            path(
                                # Only editors can request value counts
                                "delta-<int:delta_id>/result-column-value-counts.json",
                                steps.result_column_value_counts,
                            ),
                            # Security: for our users' protection, we don't allow embedding
                            # a "secret link" -- it would be too insecure.
                            path("embed", steps.embed),
                        ],
                    ),
                ),
            ]
        ),
    ),
    path("modules/<slug:module_slug>.html", modules.module_html),
    # Steps -- deprecated URLs
    #
    # The "embed" and "public_csv"/"public_json" URLs are widely used online.
    # We stopped publishing them [2021-03-18]. TODO migrate our users away from
    # them.
    path("public/moduledata/live/<int:step_id>.csv", steps.deprecated_public_csv),
    path("public/moduledata/live/<int:step_id>.json", steps.deprecated_public_json),
    url(r"^embed/(?P<step_id>[0-9]+)/?$", steps.deprecated_embed),
    # Parameters
    path(
        "oauth/create-secret/<int:workflow_id>/<int:step_id>/<slug:param>/",
        oauth.start_authorize,
    ),
    url(r"^oauth/?$", oauth.finish_authorize),
    url(r"^healthz$", health.healthz),  # kubernetes
    path("jsdata/timezones.json", jsdata.timezones.index),  # JavaScript support data
    path("manifest.json", manifest.manifest),  # Web app manifest
]
