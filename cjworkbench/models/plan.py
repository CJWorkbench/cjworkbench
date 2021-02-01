from __future__ import annotations

from django.db import models
import stripe


class Plan(models.Model):
    """(Paid) Plan a user can subscribe to."""

    class Meta:
        app_label = "cjworkbench"
        db_table = "plan"
        # for Django-Admin help
        verbose_name = "Plan (edit/delete in Stripe dashboard)"
        verbose_name_plural = "Plans (create/edit/delete in Stripe dashboard)"

    stripe_price_id = models.SlugField(unique=True)
    """Identifier on Stripe."""

    stripe_product_id = models.SlugField()
    """Identifier on Stripe. Currently unused.

    There may be many prices per product. Workbench stores them all. Mark some
    "archived" (not "active") to hide them from users.
    """

    stripe_product_name = models.TextField()
    """Text from Stripe. Not i18n-ready."""

    stripe_amount = models.PositiveIntegerField()
    """Number of cents Stripe will charge.

    See https://stripe.com/docs/api/plans/create#create_plan-amount
    """

    stripe_currency = models.CharField(max_length=3)
    """Currency Stripe will charge in.

    3-letter ISO country code, lowercased. For example: 'usd'.
    """

    stripe_active = models.BooleanField()
    """Stripe "active" (not-"archived") flag.

    When a Stripe Price is not active, we remember its Subscriptions. We don't
    display the Price anywhere aside from existing Subscriptions.
    """

    max_fetches_per_day = models.IntegerField(
        default=1000,
        help_text=(
            "Applies to the sum of all the user's Workflows. "
            "One fetch every 5min = 288 fetches per day."
        ),
    )
    """Quota for cronjobs."""

    @classmethod
    def upsert_from_stripe_product_and_price(
        cls,
        price: stripe.Price,
        product: stripe.Product,
    ) -> Plan:
        """Upsert Plan from Stripe data; return (plan, is_created)."""
        return cls.objects.update_or_create(
            stripe_price_id=price.id,
            defaults={  # Django nit: "defaults" here means, "overwrite"
                **product.metadata,
                **dict(
                    # Override product.metadata, if need be
                    stripe_product_id=product.id,
                    stripe_product_name=product.name,
                    stripe_amount=price.unit_amount,
                    stripe_currency=price.currency,
                    stripe_active=price.active,
                ),
            },
        )
