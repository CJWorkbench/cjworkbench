import os

from .util import FalsyStrings

__all__ = ("FREE_TIER_USER_LIMITS",)

FREE_TIER_USER_LIMITS = {}
if "CJW_FREE_TIER_CAN_CREATE_SECRET_LINK" in os.environ:
    FREE_TIER_USER_LIMITS["can_create_secret_link"] = (
        os.environ["CJW_FREE_TIER_CAN_CREATE_SECRET_LINK"] not in FalsyStrings
    )
if "CJW_FREE_TIER_MAX_FETCHES_PER_DAY" in os.environ:
    FREE_TIER_USER_LIMITS["max_fetches_per_day"] = int(
        os.environ["CJW_FREE_TIER_MAX_FETCHES_PER_DAY"]
    )
if "CJW_FREE_TIER_MAX_DELTA_AGE_IN_DAYS" in os.environ:
    FREE_TIER_USER_LIMITS["max_delta_age_in_days"] = int(
        os.environ["CJW_FREE_TIER_MAX_DELTA_AGE_IN_DAYS"]
    )
