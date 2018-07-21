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
import os
from allauth.account.views import SignupView
from django.conf.urls import url
from django.contrib import admin
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.views.defaults import page_not_found
from django.views.generic.base import RedirectView

urlpatterns = [
    url(r'^admin/?', admin.site.urls),
    url(r'^account/signup/$', SignupView.as_view(), name='account_signup'),
    url(r'^xyzzy/signup/$', RedirectView.as_view(url='/account/signup/', permanent=True), name='account_signup'),
    url(r'^account/', include('allauth.urls')),
    url(r'^', include('server.urls')),
]

# In integration-test environment, make GET /last-sent-email return the
# last-sent email. (No emails are _sent_: they're just appended to a list.)
if os.environ.get('CJW_MOCK_EMAIL'):
    from django.core import mail
    from django.http import HttpResponse, HttpResponseNotFound

    def last_sent_email(request):
        if not hasattr(mail, 'outbox') or not mail.outbox:
            return HttpResponseNotFound('No emails have been sent')

        email = mail.outbox[-1].message()
        return HttpResponse(email.as_bytes(),
                            content_type=email.get_content_type())

    urlpatterns.append(url(r'^last-sent-email', last_sent_email))
