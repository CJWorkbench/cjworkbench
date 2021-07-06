from __future__ import annotations

from contextlib import contextmanager
from typing import ContextManager

from django.contrib.auth.models import User
from django.db import models

from cjworkbench import i18n

from .product import Product
from .userlimits import UserLimits


class UserProfile(models.Model):
    user = models.OneToOneField(
        User, related_name="user_profile", on_delete=models.CASCADE
    )

    get_newsletter = models.BooleanField(default=False)
    """True iff the user is requesting to be part of our newsletter.

    This is sent to Intercom during sign-up, then it's ignored. Don't trust it.
    """

    max_fetches_per_day = models.IntegerField(
        default=lambda: UserLimits.free_user_limits().max_fetches_per_day,
        help_text=(
            "Applies to the sum of all this user's Workflows. "
            "One fetch every 5min = 288 fetches per day."
        ),
    )

    locale_id = models.CharField(
        max_length=5,
        default=i18n.default_locale,
        choices=[(x, x) for x in i18n.supported_locales],
    )
    """User-selected locale ID.

    This overrides the request-session locale ID. It's also used for emailed
    "new data available" notifications (for which there are no HTTP requests).
    """

    stripe_customer_id = models.SlugField(null=True, blank=True, default=None)
    """Stripe Customer ID, if set.

    We set a Stripe Customer ID when a user clicks on a "Pay" button. A User
    may have a Stripe Customer ID even if that user has never paid for anything.
    """

    @property
    def effective_limits(self):
        products = Product.objects.filter(prices__subscriptions__user_id=self.user_id)

        max_fetches_per_day = max(
            [
                self.max_fetches_per_day,
                *(product.max_fetches_per_day for product in products),
            ]
        )
        max_delta_age_in_days = max(
            [
                UserLimits.free_user_limits().max_delta_age_in_days,
                *(product.max_delta_age_in_days for product in products),
            ]
        )
        can_create_secret_link = any(
            product.can_create_secret_link for product in products
        )
        return UserLimits(
            max_fetches_per_day=max_fetches_per_day,
            max_delta_age_in_days=max_delta_age_in_days,
            can_create_secret_link=can_create_secret_link,
        )

    def __str__(self):
        return self.user.email
