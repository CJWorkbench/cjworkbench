from typing import NamedTuple


class UserLimits(NamedTuple):
    """Limits that apply to a user, based on plan.

    The defaults apply to newly-subscribed users and anonymous users.
    """

    max_fetches_per_day: int = 50
    """Number of scheduled fetches.

    Checked whenever the user tries to schedule new fetches.
    """
