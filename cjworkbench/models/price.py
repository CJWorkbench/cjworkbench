from __future__ import annotations

from django.db import models
import stripe

from .product import Product


class Price(models.Model):
    """Price a user can subscribe to."""

    class Meta:
        app_label = "cjworkbench"
        db_table = "price"
        # for Django-Admin help
        verbose_name = "Price (edit/delete in Stripe dashboard)"
        verbose_name_plural = "Prices (create/edit/delete in Stripe dashboard)"

    product = models.ForeignKey(
        Product,
        related_name="prices",
        on_delete=models.PROTECT,
    )
    """Product this Price can buy you.

    There may be many prices per product. Workbench stores them all. Mark some
    "archived" (not "active") to hide them from users.
    """

    stripe_price_id = models.SlugField(unique=True)
    """Identifier on Stripe."""

    stripe_amount = models.PositiveIntegerField()
    """Number of cents Stripe will charge.

    See https://stripe.com/docs/api/plans/create#create_plan-amount
    """

    stripe_currency = models.CharField(max_length=3)
    """Currency Stripe will charge in.

    3-letter ISO country code, lowercased. For example: 'usd'.
    """

    stripe_interval = models.TextField(
        default="month", choices=[("month", "month"), ("year", "year")]
    )
    """Whether amount+currency are charged per-month or per-year."""

    stripe_active = models.BooleanField()
    """Stripe "active" (not-"archived") flag.

    When a Stripe Price is not active, we remember its Subscriptions. We don't
    display the Price anywhere aside from existing Subscriptions.
    """
