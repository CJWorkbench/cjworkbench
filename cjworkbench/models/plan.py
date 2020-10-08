from __future__ import annotations

from django.db import models
from django.utils import timezone
import stripe


class Plan(models.Model):
    """(Paid) Plan a user can subscribe to."""

    class Meta:
        app_label = "cjworkbench"
        db_table = "plan"
        # for Django-Admin help
        verbose_name = "Plan (edit/delete in Stripe dashboard)"
        verbose_name_plural = "Plans (create/edit/delete in Stripe dashboard)"

    stripe_product_id = models.SlugField(unique=True)
    """Identifier on Stripe."""

    stripe_product_name = models.TextField()
    """Text from Stripe. Not i18n-ready."""

    stripe_price_id = models.SlugField(unique=True)
    """Identifier on Stripe.

    There may be many prices per product. For now, Workbench only stores and
    prompts for the first.
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
        cls, product: stripe.Product, price: stripe.Price
    ) -> Plan:
        """Upsert Plan from Stripe data; return (plan, is_created)."""
        return cls.objects.update_or_create(
            stripe_product_id=product.id,
            defaults={  # Django nit: "defaults" here means, "overwrite"
                **product.metadata,
                **dict(
                    # Override product.metadata, if need be
                    stripe_price_id=price.id,
                    stripe_product_name=product.name,
                ),
            },
        )
