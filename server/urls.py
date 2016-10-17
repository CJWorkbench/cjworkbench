from django.conf.urls import url

from . import views

urlpatterns = [
    # ex: /
    url(r'^$', views.index, name='index'),

    # ex: /workflows/5/
    url(r'^workflows/(?P<workflow_id>[0-9]+)/$', views.workflow, name='workflow'),

    # ex: /wfmodules/5/
    url(r'^wfmodules/(?P<wfmodule_id>[0-9]+)/$', views.WfModule, name='WfModule'),
]
