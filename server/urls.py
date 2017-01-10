from django.conf.urls import url
from django.views.generic import TemplateView
from . import views


urlpatterns = [
    # ex: /
    #    url(r'^$', views.index, name='index'),

    url(r'^$', TemplateView.as_view(template_name='index.html')),

    # list all workflows
    url(r'^workflows/$', TemplateView.as_view(template_name='workflows.html')),
    url(r'^api/workflows/?$', views.workflow_list),

    # list specific workflow ex: /workflows/5/
    url(r'^workflows/(?P<pk>[0-9]+)/$', TemplateView.as_view(template_name='workflow.html')),
    url(r'^api/workflows/(?P<pk>[0-9]+)/?$', views.workflow_detail),

    url(r'^api/workflows/(?P<pk>[0-9]+)/addmodule/?$', views.workflow_addmodule),
    url(r'^api/workflows/(?P<pk>[0-9]+)/execute/?$', views.workflow_execute),

    # modules
    url(r'^api/modules/?$', views.module_list),
    url(r'^api/modules/(?P<pk>[0-9]+)/?$', views.module_detail),

    url(r'^api/initmodules/$', views.init_modules2),


    # modules and parameters in a workflow
    url(r'^api/wfmodules/(?P<pk>[0-9]+)/?$', views.wfmodule_detail),
    url(r'^api/parameters/(?P<pk>[0-9]+)/?$', views.parameterval_detail)
]

