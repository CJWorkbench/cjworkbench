import json

from django.conf import settings
from django.http import HttpResponse, HttpRequest, JsonResponse, Http404
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import stripe

import cjworkbench.models.stripe
from cjworkbench.models.plan import Plan
from cjworkbench.models.userprofile import UserProfile


@csrf_exempt
@require_POST
def webhook(request: HttpRequest) -> HttpResponse:
    """Handle data from Stripe.

    Stripe is the authority on all Stripe-related models in our database. If a
    user request inspires us to set data, we must set it through Stripe and then
    wait for Stripe to send to the webhook. The webhook is where we write to the
    database.

    Events we handle:

        * checkout.session.completed: user subscribes
        * invoice.paid: user repays
        * invoice.payment_failed: user fails to repay

    Ref: https://stripe.com/docs/billing/subscriptions/checkout/fixed-price
    """
    sig_header = request.META["HTTP_STRIPE_SIGNATURE"]

    try:
        event = stripe.Webhook.construct_event(
            request.body, sig_header, settings.STRIPE_WEBHOOK_SIGNING_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        return HttpResponse(status=400)

    if event["type"] == "checkout.session.completed":
        checkout_session = event["data"]["object"]
        # raise on error
        cjworkbench.models.stripe.handle_checkout_session_completed(checkout_session)
    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        # raise on error
        cjworkbench.models.stripe.handle_customer_subscription_deleted(subscription)
    elif event["type"] == "customer.subscription.updated":
        subscription = event["data"]["object"]
        # raise on error
        cjworkbench.models.stripe.handle_customer_subscription_updated(subscription)
    else:
        event["data"]["object"]

    response = HttpResponse(status=204)
    if settings.DEBUG:
        # Workaround brittle stripe-listen http client + http-process-proxy http server
        # [2020-10-08] avoids lots of stripe-listen errors like:
        # [ERROR] Failed to POST: Post http://frontend:8000/stripe/webhook: EOF
        response["Connection"] = "close"  # disable keep-alive
    return response


@never_cache
@require_POST
def create_checkout_session(request: HttpRequest) -> HttpResponse:
    """Return a Stripe `checkout.session` object.

    The JavaScript client uses this object to redirect the user to Stripe's
    checkout page.

    TODO unit-test
    """
    plans = list(Plan.objects.all())
    if len(plans) == 0:
        raise Http404("Stripe is disabled")
    elif len(plans) > 1:
        raise RuntimeError(
            "There are too many Stripe plans! We only support one for now"
        )
    plan = plans[0]
    billing_url = request.build_absolute_uri(reverse("settings_billing"))
    checkout_session = cjworkbench.models.stripe.create_checkout_session(
        request.user.id, plan, billing_url
    )

    return JsonResponse(
        {
            "checkoutSession": checkout_session,
            "apiKey": settings.STRIPE_PUBLIC_API_KEY,
        }
    )


@never_cache
@require_POST
def create_billing_portal_session(request: HttpRequest) -> HttpResponse:
    """Return a Stripe `checkout.session` object.

    The JavaScript client uses this object to redirect the user to Stripe's
    checkout page.

    Raises Http404 if UserProfile.stripe_customer_id is null.
    """
    billing_url = request.build_absolute_uri(reverse("settings_billing"))
    try:
        billing_portal_session = (
            cjworkbench.models.stripe.create_billing_portal_session(
                request.user.id, billing_url
            )
        )
    except UserProfile.DoesNotExist:
        raise Http404("This user has no Stripe customer information.")

    return JsonResponse({"billingPortalSession": billing_portal_session})
