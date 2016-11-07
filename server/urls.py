from django.conf.urls import url
from django.views.generic import TemplateView
from . import views

urlpatterns = [
    # ex: /
    url(r'^$', TemplateView.as_view(template_name='index.html')),

    #    url(r'^$', views.index, name='index'),

    # ex: /workflows/5/
    url(r'^workflows/(?P<workflow_id>[0-9]+)/$', views.workflow, name='workflow'),

    # ex: /wfmodules/5/
    url(r'^wfmodules/(?P<wfmodule_id>[0-9]+)/$', views.WfModule, name='WfModule'),
]
