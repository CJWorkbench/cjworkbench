"""cjworkbench URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.views.defaults import page_not_found
from django.http import Http404
#from cjworkbench.views.signup import SignupView
from allauth.account.views import SignupView

urlpatterns = [
    url(r'^admin/?', admin.site.urls),
    url(r'^xyzzy/signup/$', SignupView.as_view(), name='account_signup'),
    url(r'^account/signup/$', page_not_found,  {'exception': Http404()}),
    url(r'^account/', include('allauth.urls')),
    url(r'^', include('server.urls')),
]
