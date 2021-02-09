import json
import time
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import override_settings
from stripe.webhook import WebhookSignature

import cjworkbench.models.stripe
from cjworkbench.models.price import Price
from cjworkbench.models.product import Product
from cjworkbench.models.userprofile import UserProfile
from cjworkbench.views.stripe import (
    webhook,
    create_checkout_session,
    create_billing_portal_session,
)
from cjworkbench.tests.utils import DbTestCase


User = get_user_model()


def create_user(
    email="user@example.org", first_name="Name", last_name="Lastname", **kwargs
):
    user = User.objects.create(email=email, first_name=first_name, last_name=last_name)
    UserProfile.objects.create(user=user, **kwargs)
    return user


def create_product(*, stripe_product_id="prod_1", stripe_product_name="Premium Plan"):
    return Product.objects.create(
        stripe_product_id=stripe_product_id, stripe_product_name=stripe_product_name
    )


def create_price(*, product, **kwargs):
    kwargs = {
        "stripe_price_id": "price_1",
        "stripe_active": True,
        "stripe_amount": 100,
        "stripe_currency": "usd",
        **kwargs,
    }
    return product.prices.create(**kwargs)


class WebhookTest(DbTestCase):
    @override_settings(STRIPE_WEBHOOK_SIGNING_SECRET="sec_123")
    def test_400_invalid_signature(self):
        response = self.client.post(
            "/stripe/webhook",
            {"type": "whatever"},
            HTTP_STRIPE_SIGNATURE="t=32141,v1=invalid",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.content,
            b"No signatures found matching the expected signature for payload",
        )

    @override_settings(STRIPE_WEBHOOK_SIGNING_SECRET="sec_123")
    def test_400_missing_signature(self):
        response = self.client.post(
            "/stripe/webhook",
            {"type": "whatever"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.content,
            b"Missing Stripe-Signature HTTP header",
        )

    @patch.object(
        cjworkbench.models.stripe,
        "handle_checkout_session_completed",
        return_value=None,
    )
    @override_settings(STRIPE_WEBHOOK_SIGNING_SECRET="sec_123")
    def test_checkout_session_completed(self, handler):
        timestamp = time.time()
        payload = json.dumps(
            {"type": "checkout.session.completed", "data": {"object": "MOCK"}}
        )
        signature = WebhookSignature._compute_signature(
            "%d.%s" % (timestamp, payload), "sec_123"
        )
        header_value = "t=%d,v1=%s" % (timestamp, signature)
        response = self.client.post(
            "/stripe/webhook",
            payload,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=header_value,
        )
        self.assertEqual(response.status_code, 204)
        handler.assert_called_with("MOCK")

    @patch.object(
        cjworkbench.models.stripe,
        "handle_customer_subscription_deleted",
        return_value=None,
    )
    @override_settings(STRIPE_WEBHOOK_SIGNING_SECRET="sec_123")
    def test_customer_subscription_deleted(self, handler):
        timestamp = time.time()
        payload = json.dumps(
            {"type": "customer.subscription.deleted", "data": {"object": "MOCK"}}
        )
        signature = WebhookSignature._compute_signature(
            "%d.%s" % (timestamp, payload), "sec_123"
        )
        header_value = "t=%d,v1=%s" % (timestamp, signature)
        response = self.client.post(
            "/stripe/webhook",
            payload,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=header_value,
        )
        self.assertEqual(response.status_code, 204)
        handler.assert_called_with("MOCK")

    @patch.object(
        cjworkbench.models.stripe,
        "handle_customer_subscription_updated",
        return_value=None,
    )
    @override_settings(STRIPE_WEBHOOK_SIGNING_SECRET="sec_123")
    def test_customer_subscription_updated(self, handler):
        timestamp = time.time()
        payload = json.dumps(
            {"type": "customer.subscription.updated", "data": {"object": "MOCK"}}
        )
        signature = WebhookSignature._compute_signature(
            "%d.%s" % (timestamp, payload), "sec_123"
        )
        header_value = "t=%d,v1=%s" % (timestamp, signature)
        response = self.client.post(
            "/stripe/webhook",
            payload,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=header_value,
        )
        self.assertEqual(response.status_code, 204)
        handler.assert_called_with("MOCK")

    @override_settings(STRIPE_WEBHOOK_SIGNING_SECRET="sec_123")
    def test_unhandled_event_accepted(self):
        timestamp = time.time()
        payload = json.dumps({"type": "some.unknown.event", "data": {"object": "MOCK"}})
        signature = WebhookSignature._compute_signature(
            "%d.%s" % (timestamp, payload), "sec_123"
        )
        header_value = "t=%d,v1=%s" % (timestamp, signature)
        response = self.client.post(
            "/stripe/webhook",
            payload,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=header_value,
        )
        self.assertEqual(response.status_code, 204)


class CreateCheckoutSessionTest(DbTestCase):
    def _post_json(self, **json_kwargs):
        return self.client.post(
            "/stripe/create-checkout-session",
            json.dumps(json_kwargs),
            content_type="application/json",
        )

    def test_require_logged_in(self):
        response = self._post_json(stripePriceId="price_123")
        self.assertEqual(response.status_code, 302)  # redirect to login

    @override_settings(STRIPE_API_KEY="key_123", STRIPE_PUBLIC_API_KEY="pk_123")
    def test_400_no_price(self):
        self.client.force_login(create_user())
        response = self._post_json()
        self.assertEqual(response.status_code, 400)

    @override_settings(STRIPE_API_KEY="key_123", STRIPE_PUBLIC_API_KEY="pk_123")
    def test_404_missing_price(self):
        self.client.force_login(create_user())
        response = self._post_json(stripePriceId="price_123")
        self.assertEqual(response.status_code, 404)

    @override_settings()
    def test_404_no_stripe_api_key(self):
        del settings.STRIPE_API_KEY  # restored because override_settings() is above
        self.client.force_login(create_user())
        create_price(product=create_product(), stripe_price_id="price_123")
        response = self._post_json(stripePriceId="price_123")
        self.assertEqual(response.status_code, 404)

    @patch.object(
        cjworkbench.models.stripe,
        "create_checkout_session",
        return_value={
            "id": "cs_123",
        },
    )
    @override_settings(STRIPE_API_KEY="key_123", STRIPE_PUBLIC_API_KEY="pubkey_123")
    def test_happy_path(self, create_checkout_session):
        user = create_user()
        self.client.force_login(user)
        price = create_price(product=create_product(), stripe_price_id="price_123")
        response = self._post_json(stripePriceId="price_123")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(
            data,
            {
                "checkoutSession": {"id": "cs_123"},
                "apiKey": "pubkey_123",
            },
        )

        # We sent the right stuff to Stripe
        create_checkout_session.assert_called_with(
            user.id, price, "http://testserver/settings/billing"
        )


class CreateBillingPortalSessionTest(DbTestCase):
    def test_require_logged_in(self):
        response = self.client.post("/stripe/create-billing-portal-session")
        self.assertEqual(response.status_code, 302)  # redirect to login

    def test_404_no_stripe_customer_id(self):
        self.client.force_login(create_user(stripe_customer_id=None))
        response = self.client.post("/stripe/create-billing-portal-session")
        self.assertEqual(response.status_code, 404)

    @patch.object(
        cjworkbench.models.stripe,
        "create_billing_portal_session",
        return_value={
            "id": "bps_123",
        },
    )
    @override_settings(STRIPE_API_KEY="key_123")
    def test_happy_path(self, create_billing_portal_session):
        user = create_user(stripe_customer_id="cus_123")
        self.client.force_login(user)
        response = self.client.post("/stripe/create-billing-portal-session")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data, {"billingPortalSession": {"id": "bps_123"}})

        # We sent the right stuff to Stripe
        create_billing_portal_session.assert_called_with(
            user.id, "http://testserver/settings/billing"
        )
