from typing import NamedTuple


class UserUsage(NamedTuple):
    """How much a user has used of the UserLimits."""

    fetches_per_day: int = 0
    """Number of scheduled fetches.

    Checked whenever the user tries to schedule new fetches.
    """
