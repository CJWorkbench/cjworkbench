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
from allauth.account.views import SignupView
from django.conf.urls import include, url
from django.contrib import admin
from django.views.generic.base import RedirectView
from cjworkbench.i18n.views import set_locale

urlpatterns = [
    url(r"^admin/?", admin.site.urls),
    url(r"^account/signup/$", SignupView.as_view(), name="account_signup"),
    url(
        r"^xyzzy/signup/$",
        RedirectView.as_view(url="/account/signup/", permanent=True),
        name="account_signup",
    ),
    url(r"^account/", include("allauth.urls")),
    url(r"^i18n/set_locale", set_locale, name="set_locale"),
    url(r"^", include("server.urls")),
]
