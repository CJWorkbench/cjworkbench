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
    url(r'^api/simpleworkflows', views.simple_workflow_list),

    # ex: /workflows/5/
    url(r'^workflows/(?P<pk>[0-9]+)/$', TemplateView.as_view(template_name='workflow.html')),

    # ex: /workflows/5/
    #url(r'^workflows/(?P<workflow_id>[0-9]+)/$', views.workflow, name='workflow'),

    # ex: /wfmodules/5/
    url(r'^wfmodules/(?P<wfmodule_id>[0-9]+)/$', views.WfModule, name='WfModule'),
]

#from rest_framework.urlpatterns import format_suffix_patterns
#urlpatterns = format_suffix_patterns(urlpatterns)

