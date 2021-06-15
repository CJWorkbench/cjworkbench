from django.contrib.auth.models import User
from django.db.models import Avg

from cjworkbench.models.userlimits import UserLimits
from cjworkbench.models.userprofile import UserProfile
from cjworkbench.models.userusage import UserUsage

from ..clientside import Null, UserUpdate


def query_user_usage(user: User) -> UserUsage:
    return UserUsage(
        fetches_per_day=user.workflows.aggregate(
            fetches_per_day=Sum("fetches_per_day")
        )["fetches_per_day"]
        or 0
    )


def query_clientside_user(user: User) -> UserUpdate:
    """Build a clientside.UserUpdate for `user`.

    The user must not be anonymous. Also, you must wrap this in a
    User.cooperative_lock.
    """

    return UserUpdate(
        display_name=workbench_user_display(user),
        email=user.email,
        is_staff=user.is_staff,
        stripe_customer_id=user.user_profile.stripe_customer_id or Null,
        limits=user.user_profile.effective_limits._asdict(),
        usage=build_user_usage(user)._asdict(),
    )
