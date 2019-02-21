from django.conf.urls import url
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView
from . import views
from .views import acl, lessons, oauth, uploads, workflows
from .views.UploadedFileView import get_uploadedfile

urlpatterns = [
    # ex: /
    #    url(r'^$', views.index, name='index'),

    url(r'^$', RedirectView.as_view(url='/workflows')),

    url(r'^api/uploadfile/?$', uploads.handle_s3),
    url(r'^api/uploadfile/([0-9]+)$', get_uploadedfile),

    # list all workflows
    url(r'^workflows/$', views.render_workflows, name='workflows'),
    url(r'^api/workflows/?$', views.workflow_list),

    url(r'^lessons/$', lessons.render_lesson_list),
    url(r'^lessons/(?P<slug>[-a-z0-9]+)/?$', lessons.render_lesson_detail),
    url(r'^courses/(?P<course_slug>[-a-z0-9]+)/(?P<lesson_slug>[-a-z0-9]+)$',
        lessons.render_course_lesson_detail),

    # workflows
    # TODO: Name the rest of the urls or implement some kind of naming scheme
    url(r'^workflows/(?P<workflow_id>[0-9]+)/$', views.render_workflow, name="workflow"),
    url(r'^api/workflows/(?P<workflow_id>[0-9]+)/?$', views.workflow_detail),

    url(r'^api/workflows/(?P<workflow_id>[0-9]+)/duplicate/?$',
        workflows.Duplicate.as_view()),

    url(r'^api/workflows/(?P<workflow_id>[0-9]+)/acl$', acl.List.as_view()),
    url(r'^api/workflows/(?P<workflow_id>[0-9]+)/acl/(?P<email>[0-9a-zA-Z-_@+.]+)$',
        acl.Entry.as_view()),

    url(r'^api/importfromgithub/?$', views.import_from_github),

    # WfModules (Modules applied in a workflow)
    url(r'^api/wfmodules/(?P<pk>[0-9]+)/?$', views.wfmodule_detail),
    url(r'^api/wfmodules/(?P<pk>[0-9]+)/tiles/v(?P<delta_id>[0-9]+)/r(?P<tile_row>[0-9]+)/c(?P<tile_column>[0-9]+).json$',
        views.wfmodule_tile),
    # TODO: "render" and "output" are bad names. Differentiate them.
    url(r'^api/wfmodules/(?P<pk>[0-9]+)/render$', views.wfmodule_render),
    url(r'^api/wfmodules/(?P<pk>[0-9]+)/output$', views.wfmodule_output),
    url(r'^api/wfmodules/(?P<pk>[0-9]+)/embeddata$', views.wfmodule_embeddata),
    url(r'^api/wfmodules/(?P<pk>[0-9]+)/value-counts$', views.wfmodule_value_counts),
    url(r'^api/wfmodules/(?P<pk>[0-9]+)/notifications', views.notifications_delete_by_wfmodule),

    url(r'^public/moduledata/live/(?P<pk>[0-9]+)\.(?P<type>(csv|json))?$', views.wfmodule_public_output),

    # Parameters
    url(r'^oauth/create-secret/(?P<workflow_id>[0-9]+)/(?P<wf_module_id>[0-9]+)/(?P<param>[-_a-zA-Z0-9]+)/',
        oauth.start_authorize),
    url(r'^oauth/?$', oauth.finish_authorize),

    # Embeds
    url(r'^embed/(?P<wfmodule_id>[0-9]+)/?$', views.embed),

    # 404
    url(r'^404/$', TemplateView.as_view(template_name='404.html')),

    # 403
    url(r'^403/$', TemplateView.as_view(template_name='403.html')),
]
