import stripe
from django.db import models


class Product(models.Model):
    """Grouping of (Stripe) Prices a user can subscribe to."""

    class Meta:
        app_label = "cjworkbench"
        db_table = "product"
        # for Django-Admin help
        verbose_name = "Product (edit/delete in Stripe dashboard)"
        verbose_name_plural = "Products (create/edit/delete in Stripe dashboard)"

    stripe_product_id = models.SlugField()
    """Identifier on Stripe."""

    stripe_product_name = models.TextField()
    """Text from Stripe. Not i18n-ready."""

    max_fetches_per_day = models.IntegerField(
        default=1000,
        help_text=(
            "Applies to the sum of all the user's Workflows. "
            "One fetch every 5min = 288 fetches per day."
        ),
    )
    """Quota for cronjobs."""

    max_delta_age_in_days = models.IntegerField(
        default=31,  # one month (applied while migrating 2021-02-02)
        help_text=(
            "Number of days a change ('Delta') lives in the undo history. "
            "Workbench deletes actions that haven't been undone in a long time."
        ),
    )
    """Quota for undo history."""

    can_create_secret_link = models.BooleanField(
        null=False,
        default=True,
        help_text="When True, user may create secret links to workflows",
    )
