import enum

from django.contrib.auth import get_user_model
from django.db import models

from .price import Price

User = get_user_model()


class StripeSubscriptionStatus(enum.Enum):
    """Stripe subscription status.

    Ref: https://stripe.com/docs/billing/subscriptions/overview#subscription-statuses
    """

    TRIALING = "trialing"
    ACTIVE = "active"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"


class Subscription(models.Model):
    """Our cached copy of Stripe's Subscription object.

    Only write to the Subscription table in response to a Stripe webhook request
    or a Stripe API response.
    """

    class Meta:
        app_label = "cjworkbench"
        db_table = "subscription"

    user = models.ForeignKey(
        User, related_name="subscriptions", on_delete=models.PROTECT
    )
    """User who is subscribed."""

    price = models.ForeignKey(
        Price, related_name="subscriptions", on_delete=models.PROTECT
    )
    """Price the subscription is for."""

    stripe_subscription_id = models.SlugField(
        blank=False,
        db_index=True,  # Webhooks look up based on subscription ID
        unique=True,
    )
    """Stripe Subscription ID."""

    stripe_status = models.CharField(
        blank=False,
        max_length=max(len(x.value) for x in StripeSubscriptionStatus),
        choices=[(x.value, x.value) for x in StripeSubscriptionStatus],
    )
    """Stripe subscription status (str).

    Call StripeSubscriptionStatus(subscription.stripe_status) for an enum.

    Ref: https://stripe.com/docs/billing/subscriptions/overview#subscription-statuses
    """

    created_at = models.DateTimeField()
    """When the Stripe Subscription was first created."""

    renewed_at = models.DateTimeField()
    """When the Stripe Subscription was last paid."""
