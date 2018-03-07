from django.conf.urls import url
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView
from . import views
from .views.StoredObject import StoredObjectView
from rest_framework import routers
from django.conf.urls import include

#external_router = routers.DefaultRouter()
#external_router.register(r'uploadfile', StoredObjectView)

urlpatterns = [
    # ex: /
    #    url(r'^$', views.index, name='index'),

    url(r'^$', RedirectView.as_view(url='/workflows')),

    url(r'^api/uploadfile/?$', StoredObjectView.as_view()),
    url(r'^api/uploadfile/(?P<qquuid>\S+)?$', StoredObjectView.as_view()),

    # list all workflows
    url(r'^workflows/$', views.render_workflows),
    url(r'^api/workflows/?$', views.workflow_list),

    # workflows
    #TODO: Name the rest of the urls or implement some kind of naming scheme
    url(r'^workflows/(?P<pk>[0-9]+)/$', views.render_workflow, name="workflow"),
    url(r'^api/workflows/(?P<pk>[0-9]+)/?$', views.workflow_detail),

    url(r'^api/workflows/(?P<pk>[0-9]+)/addmodule/?$', views.workflow_addmodule),
    url(r'^api/workflows/(?P<pk>[0-9]+)/duplicate/?$', views.workflow_duplicate),
    url(r'^api/workflows/(?P<pk>[0-9]+)/(?P<action>(undo|redo))/?$', views.workflow_undo_redo),

    # modules
    url(r'^api/modules/?$', views.module_list),
    url(r'^api/modules/(?P<pk>[0-9]+)/?$', views.module_detail),

#    url(r'^api/', include(external_router.urls)),

    url(r'^api/initmodules/$', views.init_modules2),
    url(r'^api/importfromgithub/?$', views.import_from_github),
    url(r'^api/refreshfromgithub/?$', views.refresh_from_github),

    # WfModules (Modules applied in a workflow)
    url(r'^api/wfmodules/(?P<pk>[0-9]+)/?$', views.wfmodule_detail),
    url(r'^api/wfmodules/(?P<pk>[0-9]+)/render$', views.wfmodule_render),
    url(r'^api/wfmodules/(?P<pk>[0-9]+)/output$', views.wfmodule_output), #TODO: These names are bad and basically backwards
    url(r'^api/wfmodules/(?P<pk>[0-9]+)/input$', views.wfmodule_input),
    url(r'^api/wfmodules/(?P<pk>[0-9]+)/histogram/(?P<col>.*)', views.wfmodule_histogram),
    url(r'^api/wfmodules/(?P<pk>[0-9]+)/dataversion/read', views.wfmodule_dataversion_read),
    url(r'^api/wfmodules/(?P<pk>[0-9]+)/dataversion', views.wfmodule_dataversion),
    url(r'^api/wfmodules/(?P<pk>[0-9]+)/notifications', views.notifications_delete_by_wfmodule),

    url(r'^public/moduledata/live/(?P<pk>[0-9]+)\.(?P<type>(csv|json))?$', views.wfmodule_public_output),

    # Parameters
    url(r'^api/parameters/(?P<pk>[0-9]+)/?$', views.parameterval_detail),
    url(r'^api/parameters/(?P<pk>[0-9]+)/event/?$', views.parameterval_event),

    url(r'^public/paramdata/live/(?P<pk>[0-9]+).png$', views.parameterval_png),

    # Embeds
    url(r'^embed/(?P<wfmodule_id>[0-9]+)/?$', views.embed),

    # URL endpoint to trigger internal cron jobs
    url(r'^runcron$', views.runcron),

    # Preloader testing
    url(r'^preloader/$', TemplateView.as_view(template_name='preloader.html')),

    # Preloader testing
    url(r'^signup_closed_test/$', TemplateView.as_view(template_name='signup_closed_test.html')),
]
