from django.conf.urls import url
from django.views.generic import TemplateView
from . import views


urlpatterns = [
    # ex: /
    #    url(r'^$', views.index, name='index'),

    url(r'^$', TemplateView.as_view(template_name='index.html')),

    # ex: /workflows/5/
    url(r'^api/workflows/(?P<pk>[0-9]+)/?$', views.workflow_detail),

    url(r'^workflows/$', TemplateView.as_view(template_name='workflows.html')),
    url(r'^api/workflows', views.workflow_list),

    url(r'^api/modules', views.module_list),

    # ex: /workflows/5/
    url(r'^workflows/(?P<pk>[0-9]+)/$', TemplateView.as_view(template_name='workflow.html')),

    # ex: /workflows/5/
    #url(r'^workflows/(?P<workflow_id>[0-9]+)/$', views.workflow, name='workflow'),

    # ex: /wfmodules/5/
    # url(r'^wfmodules/(?P<pk>[0-9]+)/$', views.WfModule, name='WfModule'),
    url(r'^api/wfmodules/(?P<pk>[0-9]+)/?$', views.wfmodule_detail),


    url(r'^api/initmodules/$', views.init_modules2)
]

