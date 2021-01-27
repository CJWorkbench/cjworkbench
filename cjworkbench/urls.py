from allauth.account.views import SignupView
from django.conf.urls import include, url
from django.contrib import admin
from django.urls import path
from django.views.generic.base import RedirectView
from cjworkbench.i18n.views import set_locale
from cjworkbench import views
import cjworkbench.views.settings.billing
import cjworkbench.views.settings.plan
import cjworkbench.views.stripe

urlpatterns = [
    url(r"^admin/?", admin.site.urls),
    url(r"^account/signup/$", SignupView.as_view(), name="account_signup"),
    url(
        r"^xyzzy/signup/$",
        RedirectView.as_view(url="/account/signup/", permanent=True),
    ),
    url(r"^account/", include("allauth.urls")),
    url(r"^locale", set_locale, name="set_locale"),
    # Billing
    path("settings/billing", views.settings.billing.get, name="settings_billing"),
    path("settings/plan", views.settings.plan.get),
    # Stripe
    path("stripe/webhook", views.stripe.webhook),
    path("stripe/create-checkout-session", views.stripe.create_checkout_session),
    path(
        "stripe/create-billing-portal-session",
        views.stripe.create_billing_portal_session,
    ),
    # App
    url(r"^", include("server.urls")),
]
