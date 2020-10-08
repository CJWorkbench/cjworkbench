import datetime
from typing import NamedTuple
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase
import stripe

from cjworkbench.models.plan import Plan
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


def create_plan(**kwargs):
    return Plan.objects.create(**kwargs)


class TestHandleCheckoutSessionCompleted(DbTestCase):
    @patch.object(
        stripe.Subscription,
        "retrieve",
        return_value=stripe.Subscription.construct_from(
            {
                "created": 1602166853,
                "current_period_start": 1602166853,
                "items": {"data": [{"price": {"product": "prod_123"}}]},
                "status": "active",
            },
            "api-key",
        ),
    )
    def test_create_subscription(self, retrieve_subscription):
        plan = create_plan(stripe_product_id="prod_123")
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
        user.user_profile.refresh_from_db()
        subscriptions = list(user.subscriptions.all())
        self.assertEqual(len(subscriptions), 1)
        subscription = subscriptions[0]
        self.assertEqual(subscription.plan_id, plan.id)
        self.assertEqual(subscription.stripe_subscription_id, "sub_123")
        self.assertEqual(subscription.stripe_status, "active")
        self.assertEqual(
            subscription.created_at,
            datetime.datetime(2020, 10, 8, 14, 20, 53, tzinfo=datetime.timezone.utc),
        )
        self.assertEqual(
            subscription.renewed_at,
            datetime.datetime(2020, 10, 8, 14, 20, 53, tzinfo=datetime.timezone.utc),
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
                        {"price": {"product": "prod_123"}},
                        {"price": {"product": "prod_124"}},
                    ]
                },
                "status": "active",
            },
            "api-key",
        ),
    )
    def test_value_error_when_two_items(self, retrieve_subscription):
        plan = create_plan(stripe_product_id="prod_123")
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
                "items": {"data": [{"price": {"product": "prod_123"}}]},
                "status": "active",
            },
            "api-key",
        ),
    )
    def test_plan_does_not_exist(self, retrieve_subscription):
        plan = create_plan(stripe_product_id="prod_321")  # wrong ID
        user = create_user(stripe_customer_id="cus_123")
        with self.assertRaises(Plan.DoesNotExist):
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
                "items": {"data": [{"price": {"product": "prod_123"}}]},
                "status": "active",
            },
            "api-key",
        ),
    )
    def test_user_profile_does_not_exist(self, retrieve_subscription):
        plan = create_plan(stripe_product_id="prod_123")
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
        plan = create_plan(stripe_product_id="prod_123")
        user = create_user(stripe_customer_id="cus_123")
        subscription = user.subscriptions.create(
            plan=plan,
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
        plan = create_plan(stripe_product_id="prod_123")
        handle_customer_subscription_deleted(
            stripe.Subscription.construct_from({"id": "sub_123"}, "api-key")
        )
        self.assertEqual(Subscription.objects.count(), 0)


class TestHandleCustomerSubscriptionUpdated(DbTestCase):
    def test_update_existing_subscription(self):
        plan = create_plan(stripe_product_id="prod_123")
        user = create_user(stripe_customer_id="cus_123")
        subscription = user.subscriptions.create(
            plan=plan,
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
            datetime.datetime(2020, 10, 8, 14, 20, 53, tzinfo=datetime.timezone.utc),
        )

    def test_update_missing_subscription(self):
        plan = create_plan(stripe_product_id="prod_123")
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
    def test_reuse_existing_stripe_customer_id(self, create_session):
        user = create_user(stripe_customer_id="cus_123", locale_id="fr")
        plan = Plan.objects.create(stripe_price_id="price_123")
        checkout_session = create_checkout_session(user.id, plan, "https://example.com")
        self.assertTrue(create_session.called)
        _, kwargs = create_session.call_args
        # Sends correct params to Stripe
        self.assertEqual(kwargs["customer"], "cus_123")
        self.assertEqual(kwargs["line_items"], [{"price": "price_123", "quantity": 1}])
        self.assertEqual(kwargs["locale"], "fr")
        self.assertEqual(kwargs["success_url"], "https://example.com")
        self.assertEqual(kwargs["cancel_url"], "https://example.com")
        self.assertEqual(kwargs["mode"], "subscription")
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
    def test_assign_new_stripe_customer_id(self, create_customer, create_session):
        user = create_user(
            email="alice@example.org",
            first_name="Alice",
            last_name="Smith",
            stripe_customer_id=None,
            locale_id="fr",
        )
        plan = Plan.objects.create(stripe_price_id="price_123")
        checkout_session = create_checkout_session(user.id, plan, "https://example.com")

        # stripe.Customer.create was called as expected
        self.assertTrue(create_customer.called)
        _, kwargs = create_customer.call_args
        self.assertEqual(kwargs["email"], "alice@example.org")
        self.assertEqual(kwargs["name"], "Alice Smith")
        self.assertEqual(kwargs["preferred_locales"], ["fr"])

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
    def test_assign_new_customer_before_stripe_checkout_session_error(
        self, create_customer, create_session
    ):
        user = create_user(stripe_customer_id=None)
        plan = Plan.objects.create(stripe_price_id="price_123")
        with self.assertRaises(RuntimeError):
            create_checkout_session(user.id, plan, "https://example.com")

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
    def test_use_existing_stripe_customer_id(self, create_session):
        user = create_user(stripe_customer_id="cus_123")
        session = create_billing_portal_session(user.id, "https://example.com")

        self.assertTrue(create_session.called)
        _, kwargs = create_session.call_args
        # Sends correct params to Stripe
        self.assertEqual(kwargs["customer"], "cus_123")
        self.assertEqual(kwargs["return_url"], "https://example.com")
        # Returns correct response
        self.assertEqual(session.id, "bps_123")

    def test_user_profile_not_found_if_no_stripe_customer_id(self):
        user = create_user(stripe_customer_id=None)
        with self.assertRaises(UserProfile.DoesNotExist):
            create_billing_portal_session(user.id, "https://example.com")
