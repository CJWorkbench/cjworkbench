from cjworkbench.models.userprofile import UserProfile
from cjworkbench.models.userlimits import UserLimits
from cjwstate.models import Workflow, Step


def isoformat(dt) -> str:
    return dt.isoformat()[: -len("000+00:00")] + "Z"


def list_autofetches_json(scope):
    """
    List all the scope's user's autofetches.

    This runs a database query. Use @database_sync_to_async around it.
    """
    autofetches = list(
        Step.objects.filter(
            auto_update_data=True,
            is_deleted=False,
            tab__is_deleted=False,
            tab__workflow_id__in=Workflow.owned_by_user_session(
                scope["user"], scope["session"]
            ),
        )
        .order_by("update_interval", "tab__workflow__creation_date", "tab__id", "id")
        .values(
            "tab__workflow_id",
            "tab__workflow__name",
            "tab__workflow__creation_date",
            "tab__workflow__last_viewed_at",
            "tab__slug",
            "tab__name",
            "id",
            "order",
            "update_interval",
        )
    )

    try:
        user_limits = scope["user"].user_profile.effective_limits
    except AttributeError:
        # scope["user"].user_profile is None ... e.g. anonymous user
        user_limits = UserLimits()

    n_fetches_per_day = sum([86400.0 / row["update_interval"] for row in autofetches])

    return {
        "maxFetchesPerDay": user_limits.max_fetches_per_day,
        "nFetchesPerDay": n_fetches_per_day,
        "autofetches": [
            {
                "workflow": {
                    "id": row["tab__workflow_id"],
                    "name": row["tab__workflow__name"],
                    "createdAt": (isoformat(row["tab__workflow__creation_date"])),
                    "lastViewedAt": (isoformat(row["tab__workflow__last_viewed_at"])),
                },
                "tab": {"slug": row["tab__slug"], "name": row["tab__name"]},
                "step": {
                    "id": row["id"],
                    "order": row["order"],
                    "fetchInterval": row["update_interval"],
                },
            }
            for row in autofetches
        ],
    }
