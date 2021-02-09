import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpRequest, JsonResponse, Http404
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import stripe

import cjworkbench.models.stripe
from cjworkbench.models.price import Price
from cjworkbench.models.userprofile import UserProfile


@csrf_exempt
@require_POST
def webhook(request: HttpRequest) -> HttpResponse:
    """Handle data from Stripe.

    Stripe is the authority on all Stripe-related fields in our database. If a
    user request inspires us to set data, that data will not touch our database
    until Stripe sends it to us -- either via API responses or via this webhook.

    Events we handle:

        * checkout.session.completed
        * customer.subscription.deleted
        * customer.subscription.updated

    Ref: https://stripe.com/docs/billing/subscriptions/checkout/fixed-price
    """
    try:
        sig_header = request.META["HTTP_STRIPE_SIGNATURE"]
    except KeyError:
        return HttpResponse(
            "Missing Stripe-Signature HTTP header",
            content_type="text/plain; charset=utf-8",
            status=400,
        )

    try:
        event = stripe.Webhook.construct_event(
            request.body, sig_header, settings.STRIPE_WEBHOOK_SIGNING_SECRET
        )
        obj = event["data"]["object"]
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        return HttpResponse(
            str(e), content_type="text/plain; charset=utf-8", status=400
        )

    if event["type"] == "checkout.session.completed":
        # raise on error
        cjworkbench.models.stripe.handle_checkout_session_completed(obj)
    elif event["type"] == "customer.subscription.deleted":
        # raise on error
        cjworkbench.models.stripe.handle_customer_subscription_deleted(obj)
    elif event["type"] == "customer.subscription.updated":
        # raise on error
        cjworkbench.models.stripe.handle_customer_subscription_updated(obj)

    response = HttpResponse(status=204)
    if settings.DEBUG:
        # Workaround brittle stripe-listen http client + http-process-proxy http server
        # [2020-10-08] avoids lots of stripe-listen errors like:
        # [ERROR] Failed to POST: Post http://frontend:8000/stripe/webhook: EOF
        response["Connection"] = "close"  # disable keep-alive
    return response


@never_cache
@login_required
@require_POST
def create_checkout_session(request: HttpRequest) -> HttpResponse:
    """Return a Stripe `checkout.session` object.

    The JavaScript client uses this object to redirect the user to Stripe's
    checkout page.
    """
    if not hasattr(settings, "STRIPE_PUBLIC_API_KEY") or not hasattr(
        settings, "STRIPE_API_KEY"
    ):
        raise Http404("Stripe is disabled: there is no API key")

    try:
        stripe_price_id = str(json.loads(request.body)["stripePriceId"])
    except (TypeError, ValueError, KeyError):
        return JsonResponse(
            {"error": "You must pass a JSON { stripePriceId } Object"}, status=400
        )

    try:
        price = Price.objects.get(stripe_price_id=stripe_price_id)
    except Price.DoesNotExist:
        raise Http404("You requested a Price that does not exist")

    billing_url = request.build_absolute_uri(reverse("settings_billing"))
    checkout_session = cjworkbench.models.stripe.create_checkout_session(
        request.user.id, price, billing_url
    )

    return JsonResponse(
        {
            "checkoutSession": checkout_session,
            "apiKey": settings.STRIPE_PUBLIC_API_KEY,
        }
    )


@never_cache
@login_required
@require_POST
def create_billing_portal_session(request: HttpRequest) -> HttpResponse:
    """Return a Stripe `checkout.session` object.

    The JavaScript client uses this object to redirect the user to Stripe's
    checkout page.

    Raise Http404 if UserProfile.stripe_customer_id is null.
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
