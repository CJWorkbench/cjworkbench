from typing import ContextManager

from allauth.account.utils import user_display
from django.contrib.auth import get_user_model
from django.db import models

from cjworkbench import i18n

from .db_object_cooperative_lock import (
    DbObjectCooperativeLock,
    lookup_and_cooperative_lock,
)
from .product import Product
from .userlimits import UserLimits

User = get_user_model()


class UserProfile(models.Model):
    user = models.OneToOneField(
        User, related_name="user_profile", on_delete=models.CASCADE
    )

    get_newsletter = models.BooleanField(default=False)
    """True iff the user is requesting to be part of our newsletter.

    There is a race here. TODO delete this field and query our mass-mail
    service instead.
    """

    max_fetches_per_day = models.IntegerField(
        default=UserLimits().max_fetches_per_day,
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
                UserLimits().max_delta_age_in_days,
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
        return user_display(self.user) + " (" + self.user.email + ")"

    @classmethod
    def lookup_and_cooperative_lock(
        cls, **kwargs
    ) -> ContextManager[DbObjectCooperativeLock]:
        """Yield in a database transaction with an object selected FOR UPDATE.

        Example:

            with UserProfile.lookup_and_cooperative_lock(user_id=123) as lock:
                user_profile = lock.user_profile
                # ... do stuff
                lock.after_commit(lambda: print("called after commit, before True is returned"))
                return True

        This is _cooperative_. It only works if every write uses this method.

        It is safe to call cooperative_lock() within a cooperative_lock(). The inner
        one will behave as a no-op.

        If the context-managed block raises an error, that error will be re-raised
        and no further callbacks will be called.

        If any registered callback raises an error, that error will be re-raised
        and no further callbacks will be called.

        If any registered callback accesses the database, that will (obviously) be
        _outside_ the transaction, with the object _unlocked_.

        Take care with async functions. Transactions don't cross async boundaries;
        anything you `await` while you hold the cooperative lock won't be rolled
        back with the same rules as non-awaited code. You can still use
        cooperative locking; but instead of behaving like a database transaction,
        it will behave like a simple advisory lock; and _it cannot be nested_.

        Raises UserProfile.DoesNotExist. Re-raises any error from the inner code
        block and registered callbacks.
        """
        return lookup_and_cooperative_lock(cls.objects, "user_profile", **kwargs)
