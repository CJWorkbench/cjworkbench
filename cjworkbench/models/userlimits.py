from typing import NamedTuple


class UserLimits(NamedTuple):
    """Limits that apply to a user, based on plan.

    The defaults apply to newly-subscribed users and anonymous users.
    """

    max_fetches_per_day: int = 5
    """Number of scheduled fetches.

    Checked whenever the user tries to schedule new fetches.
    """

    max_delta_age_in_days: int = 3
    """Cutoff after which we delete owned Workflows' Deltas.

    Checked in a cronjob. Workflows are joined with their owners' UserProfiles
    to determine max_delta_age_in_days.
    """

    can_create_secret_link: bool = False
    """When True, user may create a secret link."""
