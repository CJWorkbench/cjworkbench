import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
import stripe

from cjworkbench.models.price import Price
from cjworkbench.models.subscription import Subscription
from cjworkbench.models.userprofile import UserProfile


def _unix_timestamp_to_datetime(timestamp: int) -> datetime.datetime:
    return datetime.datetime.utcfromtimestamp(timestamp).astimezone(
        datetime.timezone.utc
    )


def create_checkout_session(
    user_id: int, price: Price, billing_url: str
) -> stripe.checkout.Session:
    """Create a Stripe CheckoutSession, suitable for a JsonResponse.

    Ref: https://stripe.com/docs/billing/subscriptions/checkout/fixed-price#create-a-checkout-session

    Create a Stripe Customer for the given User if the User does not already
    have one.

    Re-raise Stripe error if creating a Customer or CheckoutSession fails.
    """
    with UserProfile.lookup_and_cooperative_lock(user_id=user_id) as user_profile:
        user = user_profile.user
        if user_profile.stripe_customer_id is None:
            stripe_customer = stripe.Customer.create(
                email=user.email,
                name=user.get_full_name(),
                preferred_locales=[user_profile.locale_id],
                api_key=settings.STRIPE_API_KEY,
            )
            user_profile.stripe_customer_id = stripe_customer.id
            user_profile.save(update_fields=["stripe_customer_id"])
            # COMMIT before creating checkout session. Otherwise, if we fail to create a
            # Session the user_profile.stripe_customer_id will be reset.

    return stripe.checkout.Session.create(
        customer=user_profile.stripe_customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price.stripe_price_id, "quantity": 1}],
        locale=user_profile.locale_id,
        success_url=billing_url,
        cancel_url=billing_url,
        mode="subscription",
        api_key=settings.STRIPE_API_KEY,
    )


def create_billing_portal_session(
    user_id: int, billing_url: str
) -> stripe.billing_portal.Session:
    """Create a Stripe BillingPortalSession, suitable for a JsonResponse.

    Ref: https://stripe.com/docs/api/customer_portal/object

    Raise UserProfile.DoesNotExist if the user does not have a Stripe customer ID.
    Re-raise Stripe error if creating a BillingPortalSession fails.
    """
    # raises UserProfile.DoesNotExist
    with UserProfile.lookup_and_cooperative_lock(
        user_id=user_id, stripe_customer_id__isnull=False
    ) as user_profile:
        stripe_customer_id = user_profile.stripe_customer_id

    return stripe.billing_portal.Session.create(
        customer=stripe_customer_id,
        return_url=billing_url,
        api_key=settings.STRIPE_API_KEY,
    )


def handle_checkout_session_completed(
    checkout_session: stripe.api_resources.checkout.Session,
) -> None:
    """Create a Subscription based on a Stripe Webhook call.

    Assumes the Subscription is for a Stripe Customer we already created. See
    UserProfile.stripe_customer_id.

    1. Request Subscription and Customer details from Stripe.
    2. Find UserProfile with stripe_customer_id == Customer.id.
    3. Upsert Subscription based on stripe_subscription_id.

    Raise error (intended to cause 500 Server Error) on any problem. Tested:

    [✓] ValueError if Stripe data does not match expectations.
    [✓] Price.DoesNotExist if subscribed to a non-price.
    [✓] UserProfile.DoesNotExist if customer cannot be found in our database.
    """
    stripe_subscription_id = checkout_session.subscription
    stripe_customer_id = checkout_session.customer
    stripe_subscription = stripe.Subscription.retrieve(
        stripe_subscription_id,
        api_key=settings.STRIPE_API_KEY,
    )  # Raise all sorts of errors
    items = stripe_subscription["items"].data  # not ".items": stripe-python is weird
    if len(items) != 1:
        raise ValueError("len(items) != 1")
    item = items[0]
    price = Price.objects.get(stripe_price_id=item.price.id)  # raise Price.DoesNotExist

    with UserProfile.lookup_and_cooperative_lock(
        stripe_customer_id=stripe_customer_id
    ) as user_profile:  # raise UserProfile.NotFound
        user = user_profile.user
        user.subscriptions.update_or_create(
            stripe_subscription_id=stripe_subscription_id,
            defaults=dict(
                price=price,
                stripe_status=stripe_subscription.status,
                created_at=_unix_timestamp_to_datetime(stripe_subscription.created),
                renewed_at=_unix_timestamp_to_datetime(
                    stripe_subscription.current_period_start
                ),
            ),
        )


def handle_customer_subscription_deleted(
    stripe_subscription: stripe.Subscription,
) -> None:
    """Delete a Subscription based on a Stripe Webhook call.

    No-op if the Subscription does not exist.
    """
    Subscription.objects.filter(stripe_subscription_id=stripe_subscription.id).delete()


def handle_customer_subscription_updated(
    stripe_subscription: stripe.Subscription,
) -> None:
    """Update a Subscription based on a Stripe Webhook call.

    No-op if the Subscription does not exist.
    """
    Subscription.objects.filter(stripe_subscription_id=stripe_subscription.id).update(
        renewed_at=_unix_timestamp_to_datetime(
            stripe_subscription.current_period_start
        ),
        stripe_status=stripe_subscription.status,
    )
