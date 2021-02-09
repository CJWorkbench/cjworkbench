import datetime
from typing import NamedTuple
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
import stripe

from cjworkbench.models.price import Price
from cjworkbench.models.product import Product
from cjworkbench.models.stripe import (
    create_checkout_session,
    create_billing_portal_session,
    handle_checkout_session_completed,
    handle_customer_subscription_deleted,
    handle_customer_subscription_updated,
)
from cjworkbench.models.subscription import Subscription
from cjworkbench.models.userprofile import UserProfile
from ..utils import DbTestCase

User = get_user_model()


def create_user(
    email="user@example.org", first_name="Name", last_name="Lastname", **kwargs
):
    user = User.objects.create(email=email, first_name=first_name, last_name=last_name)
    UserProfile.objects.create(user=user, **kwargs)
    return user


def create_product(*, stripe_product_id="prod_1", stripe_product_name="name"):
    return Product.objects.create(
        stripe_product_id="prod_1", stripe_product_name="name"
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


class TestHandleCheckoutSessionCompleted(DbTestCase):
    @patch.object(
        stripe.Subscription,
        "retrieve",
        return_value=stripe.Subscription.construct_from(
            {
                "created": 1602166853,
                "current_period_start": 1602166853,
                "items": {"data": [{"price": {"id": "price_123"}}]},
                "status": "active",
            },
            "api-key",
        ),
    )
    @override_settings(STRIPE_API_KEY="key_123")
    def test_create_subscription(self, retrieve_subscription):
        price = create_price(product=create_product(), stripe_price_id="price_123")
        user = create_user(stripe_customer_id="cus_123")
        handle_checkout_session_completed(
            stripe.api_resources.checkout.Session.construct_from(
                dict(
                    subscription="sub_123",
                    customer="cus_123",
                    client_reference_id=str(user.id),
                ),
                "api-key",
            )
        )

        # Test we sent Stripe the right stuff
        self.assertTrue(retrieve_subscription.called)
        args, kwargs = retrieve_subscription.call_args
        self.assertEqual(args, ("sub_123",))
        self.assertEqual(kwargs["api_key"], "key_123")

        # Test we created the subscription in the DB
        user.user_profile.refresh_from_db()
        subscriptions = list(user.subscriptions.all())
        self.assertEqual(len(subscriptions), 1)
        subscription = subscriptions[0]
        self.assertEqual(subscription.price_id, price.id)
        self.assertEqual(subscription.stripe_subscription_id, "sub_123")
        self.assertEqual(subscription.stripe_status, "active")
        self.assertEqual(
            subscription.created_at,
            datetime.datetime(2020, 10, 8, 14, 20, 53),
        )
        self.assertEqual(
            subscription.renewed_at,
            datetime.datetime(2020, 10, 8, 14, 20, 53),
        )

    @patch.object(
        stripe.Subscription,
        "retrieve",
        return_value=stripe.Subscription.construct_from(
            {
                "created": 1602166853,
                "current_period_start": 1602166853,
                "items": {
                    "data": [
                        {"price": {"id": "price_123"}},
                        {"price": {"id": "price_124"}},
                    ]
                },
                "status": "active",
            },
            "api-key",
        ),
    )
    @override_settings(STRIPE_API_KEY="key_123")
    def test_value_error_when_two_items(self, retrieve_subscription):
        create_price(product=create_product(), stripe_price_id="price_123")
        user = create_user(stripe_customer_id="cus_123")
        with self.assertRaises(ValueError):
            handle_checkout_session_completed(
                stripe.api_resources.checkout.Session.construct_from(
                    dict(
                        subscription="sub_123",
                        customer="cus_123",
                        client_reference_id=str(user.id),
                    ),
                    "api-key",
                )
            )

    @patch.object(
        stripe.Subscription,
        "retrieve",
        return_value=stripe.Subscription.construct_from(
            {
                "created": 1602166853,
                "current_period_start": 1602166853,
                "items": {"data": [{"price": {"id": "price_123"}}]},
                "status": "active",
            },
            "api-key",
        ),
    )
    @override_settings(STRIPE_API_KEY="key_123")
    def test_plan_does_not_exist(self, retrieve_subscription):
        create_price(product=create_product(), stripe_price_id="price_321")  # wrong ID
        user = create_user(stripe_customer_id="cus_123")
        with self.assertRaises(Price.DoesNotExist):
            handle_checkout_session_completed(
                stripe.api_resources.checkout.Session.construct_from(
                    dict(
                        subscription="sub_123",
                        customer="cus_123",
                        client_reference_id=str(user.id),
                    ),
                    "api-key",
                )
            )

    @patch.object(
        stripe.Subscription,
        "retrieve",
        return_value=stripe.Subscription.construct_from(
            {
                "created": 1602166853,
                "current_period_start": 1602166853,
                "items": {"data": [{"price": {"id": "price_123"}}]},
                "status": "active",
            },
            "api-key",
        ),
    )
    @override_settings(STRIPE_API_KEY="key_123")
    def test_user_profile_does_not_exist(self, retrieve_subscription):
        create_price(product=create_product(), stripe_price_id="price_123")
        user = create_user(stripe_customer_id="cus_321")  # wrong user
        with self.assertRaises(UserProfile.DoesNotExist):
            handle_checkout_session_completed(
                stripe.api_resources.checkout.Session.construct_from(
                    dict(
                        subscription="sub_123",
                        customer="cus_123",
                        client_reference_id=str(user.id),
                    ),
                    "api-key",
                )
            )


class TestHandleCustomerSubscriptionDeleted(DbTestCase):
    def test_delete_existing_subscription(self):
        price = create_price(product=create_product(), stripe_price_id="price_123")
        user = create_user(stripe_customer_id="cus_123")
        subscription = user.subscriptions.create(
            price=price,
            stripe_subscription_id="sub_123",
            created_at=datetime.datetime.now().astimezone(datetime.timezone.utc),
            renewed_at=datetime.datetime.now().astimezone(datetime.timezone.utc),
            stripe_status="active",
        )

        handle_customer_subscription_deleted(
            stripe.Subscription.construct_from({"id": "sub_123"}, "api-key")
        )
        self.assertEqual(Subscription.objects.count(), 0)

    def test_delete_missing_subscription(self):
        price = create_price(product=create_product())
        handle_customer_subscription_deleted(
            stripe.Subscription.construct_from({"id": "sub_123"}, "api-key")
        )
        self.assertEqual(Subscription.objects.count(), 0)


class TestHandleCustomerSubscriptionUpdated(DbTestCase):
    def test_update_existing_subscription(self):
        price = create_price(product=create_product())
        user = create_user(stripe_customer_id="cus_123")
        subscription = user.subscriptions.create(
            price=price,
            stripe_subscription_id="sub_123",
            created_at=datetime.datetime.now().astimezone(datetime.timezone.utc),
            renewed_at=datetime.datetime.now().astimezone(datetime.timezone.utc),
            stripe_status="active",
        )

        handle_customer_subscription_updated(
            stripe.Subscription.construct_from(
                {
                    "id": "sub_123",
                    "status": "unpaid",
                    "current_period_start": 1602166853,
                },
                "api-key",
            )
        )
        subscription.refresh_from_db()
        self.assertEqual(subscription.stripe_status, "unpaid")
        self.assertEqual(
            subscription.renewed_at,
            datetime.datetime(2020, 10, 8, 14, 20, 53),
        )

    def test_update_missing_subscription(self):
        price = create_price(product=create_product())
        # Don't crash
        handle_customer_subscription_updated(
            stripe.Subscription.construct_from(
                {
                    "id": "sub_123",
                    "status": "unpaid",
                    "current_period_start": 1602166853,
                },
                "api-key",
            )
        )


class TestCreateCheckoutSession(DbTestCase):
    @patch.object(
        stripe.api_resources.checkout.Session,
        "create",
        return_value=stripe.api_resources.checkout.Session.construct_from(
            {"id": "cs_123"}, "api-key"
        ),
    )
    @override_settings(STRIPE_API_KEY="key_123")
    def test_reuse_existing_stripe_customer_id(self, create_session):
        user = create_user(stripe_customer_id="cus_123", locale_id="fr")
        price = create_price(product=create_product(), stripe_price_id="price_123")
        checkout_session = create_checkout_session(
            user.id, price, "https://example.com"
        )
        self.assertTrue(create_session.called)
        _, kwargs = create_session.call_args

        # Sends correct params to Stripe
        self.assertEqual(kwargs["customer"], "cus_123")
        self.assertEqual(kwargs["line_items"], [{"price": "price_123", "quantity": 1}])
        self.assertEqual(kwargs["locale"], "fr")
        self.assertEqual(kwargs["success_url"], "https://example.com")
        self.assertEqual(kwargs["cancel_url"], "https://example.com")
        self.assertEqual(kwargs["mode"], "subscription")
        self.assertEqual(kwargs["api_key"], "key_123")

        # Returns correct response
        self.assertEqual(checkout_session.id, "cs_123")

    @patch.object(
        stripe.api_resources.checkout.Session,
        "create",
        return_value=stripe.api_resources.checkout.Session.construct_from(
            {"id": "cs_123"}, "api-key"
        ),
    )
    @patch.object(
        stripe.Customer,
        "create",
        return_value=stripe.Customer.construct_from({"id": "cus_123"}, "api-key"),
    )
    @override_settings(STRIPE_API_KEY="key_123")
    def test_assign_new_stripe_customer_id(self, create_customer, create_session):
        user = create_user(
            email="alice@example.org",
            first_name="Alice",
            last_name="Smith",
            stripe_customer_id=None,
            locale_id="fr",
        )
        price = create_price(product=create_product(), stripe_price_id="price_123")
        checkout_session = create_checkout_session(
            user.id, price, "https://example.com"
        )

        # stripe.Customer.create was called as expected
        self.assertTrue(create_customer.called)
        _, kwargs = create_customer.call_args
        self.assertEqual(kwargs["email"], "alice@example.org")
        self.assertEqual(kwargs["name"], "Alice Smith")
        self.assertEqual(kwargs["preferred_locales"], ["fr"])
        self.assertEqual(kwargs["api_key"], "key_123")

        # UserProfile was updated
        user.user_profile.refresh_from_db()
        self.assertEqual(user.user_profile.stripe_customer_id, "cus_123")

        # Session was created and returned
        self.assertTrue(create_session.called)
        _, kwargs = create_session.call_args
        self.assertEqual(kwargs["customer"], "cus_123")
        self.assertEqual(checkout_session.id, "cs_123")

    @patch.object(
        stripe.api_resources.checkout.Session, "create", side_effect=RuntimeError
    )
    @patch.object(
        stripe.Customer,
        "create",
        return_value=stripe.Customer.construct_from({"id": "cus_123"}, "api-key"),
    )
    @override_settings(STRIPE_API_KEY="key_123")
    def test_assign_new_customer_before_stripe_checkout_session_error(
        self, create_customer, create_session
    ):
        user = create_user(stripe_customer_id=None)
        price = create_price(product=create_product(), stripe_price_id="price_123")
        with self.assertRaises(RuntimeError):
            create_checkout_session(user.id, price, "https://example.com")

        user.user_profile.refresh_from_db()
        self.assertEqual(user.user_profile.stripe_customer_id, "cus_123")


class TestCreateBillingPortalSession(DbTestCase):
    @patch.object(
        stripe.billing_portal.Session,
        "create",
        return_value=stripe.billing_portal.Session.construct_from(
            {"id": "bps_123"}, "api-key"
        ),
    )
    @override_settings(STRIPE_API_KEY="key_123")
    def test_use_existing_stripe_customer_id(self, create_session):
        user = create_user(stripe_customer_id="cus_123")
        session = create_billing_portal_session(user.id, "https://example.com")

        # Sends correct params to Stripe
        self.assertTrue(create_session.called)
        _, kwargs = create_session.call_args
        self.assertEqual(kwargs["customer"], "cus_123")
        self.assertEqual(kwargs["return_url"], "https://example.com")
        self.assertEqual(kwargs["api_key"], "key_123")

        # Returns correct response
        self.assertEqual(session.id, "bps_123")

    def test_user_profile_not_found_if_no_stripe_customer_id(self):
        user = create_user(stripe_customer_id=None)
        with self.assertRaises(UserProfile.DoesNotExist):
            create_billing_portal_session(user.id, "https://example.com")
