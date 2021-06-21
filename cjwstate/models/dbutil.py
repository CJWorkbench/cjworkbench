from typing import List

from django.db import connection
from django.db.models import F, QuerySet, Sum
from django.contrib.auth.models import User

from cjworkbench.models.userlimits import UserLimits
from cjworkbench.models.userprofile import UserProfile
from cjworkbench.models.userusage import UserUsage

from ..clientside import Null, UserUpdate


def make_gap_in_list(queryset: QuerySet, field: str, position: int) -> None:
    """Alter objects' `field` value so there is a gap at `position`.

    For instance: `make_gap_in_list(workflow.blocks, 'position', 3)` will
    set `.position = .position + 1` for all positions `>= 3`.

    This must be called within a database transaction.

    This ought to be a single `UPDATE`. However, Postgres checks uniqueness
    constraints _before the statement ends_, so it leads to a conflict.
    TODO use Django 3.1 with DEFERRABLE INITIALLY DEFFERED constraint to avoid
    this problem. In the meantime, write one row at a time to avoid conflict.
    """
    for id, old_position in (
        queryset.filter(**{("%s__gte" % field): position})
        .order_by("-%s" % field)
        .values_list("id", field)
    ):
        queryset.filter(id=id).update(**{field: old_position + 1})


def remove_gap_from_list(queryset: QuerySet, field: str, position: int) -> None:
    """Alter objects' `field` value so there is a gap at `position`.

    For instance: `remove_gap_from_list(workflow.blocks, 'position', 3)` will
    set `.position = .position - 1` for all positions `> 3`.

    This must be called within a database transaction.

    This ought to be a single `UPDATE`. However, Postgres checks uniqueness
    constraints _before the statement ends_, so it leads to a conflict.
    TODO use Django 3.1 with DEFERRABLE INITIALLY DEFFERED constraint to avoid
    this problem. In the meantime, write one row at a time to avoid conflict.
    """
    for id, old_position in (
        queryset.filter(**{("%s__gt" % field): position})
        .order_by(field)
        .values_list("id", field)
    ):
        queryset.filter(id=id).update(**{field: old_position - 1})


def reorder_list_by_slugs(queryset: QuerySet, field: str, slugs: List[str]) -> None:
    """Alter objects' `field` value so slugs[0] is at position 0 and so on.

    For instance:
    `remove_gap_from_list(workflow.blocks, 'position', ["block-1", "block-2")`
    will set `.position = 0` for block-1 and `.position = 1` for block-2.

    This must be called within a database transaction.

    This could be a single `UPDATE`. However, Postgres checks uniqueness
    constraints _before the statement ends_, so it leads to a conflict.
    TODO use Django 3.1 with DEFERRABLE INITIALLY DEFFERED constraint to avoid
    this problem. In the meantime, write one row at a time to avoid conflict.
    """
    # Make sure we don't overwrite any positions: make all existing numbers
    # negative.
    assert queryset.count() == len(slugs)
    queryset.update(**{field: -1 - F(field)})
    for position, slug in enumerate(slugs):
        queryset.filter(slug=slug).update(**{field: position})


def user_display_name(user: User) -> str:
    return (user.first_name + " " + user.last_name).strip() or user.email


def lock_user_by_id(user_id: int, *, for_write: bool) -> None:
    """Lock the given user until the end of the transaction.

    The user must be locked whenever reading or writing data pertaining to
    itself or its profile.

    As an illustrative example: since Alice sees "used fetches/day" as a
    property of her "user" object, lock her user object for_write whenever you
    delete a Workflow that has auto-fetches.

    ref: https://github.com/CJWorkbench/cjworkbench/wiki/Locks-and-Races#user-updates

    Raise User.DoesNotExist if the User does not exist.

    Raise RuntimeError if the caller didn't wrap us in `transaction.atomic()`.
    """
    if not connection.in_atomic_block:
        raise RuntimeError(
            "lock_user_by_id() must be called within transaction.atomic()"
        )

    if for_write:
        sql = "SELECT 1 FROM auth_user WHERE id = %s FOR UPDATE"
    else:
        sql = "SELECT 1 FROM auth_user WHERE id = %s FOR SHARE"

    with connection.cursor() as cursor:
        cursor.execute(sql, [user_id])
        if not cursor.fetchall():
            raise User.DoesNotExist


def query_user_usage(user_id: int) -> UserUsage:
    """Return user's usage.

    You must call `lock_user_by_id()` before calling this.
    """

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COALESCE(SUM(fetches_per_day), 0)
            FROM workflow
            WHERE owner_id = %s
            """,
            [user_id],
        )
        fetches_per_day = cursor.fetchall()[0][0]

    return UserUsage(fetches_per_day=fetches_per_day)


def query_clientside_user(user_id: int) -> UserUpdate:
    """Build a clientside.UserUpdate by querying the database.

    You must call `lock_user_by_id()` before calling this.
    """

    user = User.objects.get(id=user_id)
    subscribed_stripe_product_ids = list(
        user.subscriptions.select_related("price__product").values_list(
            "price__product__stripe_product_id", flat=True
        )
    )

    return UserUpdate(
        display_name=user_display_name(user),
        email=user.email,
        is_staff=user.is_staff,
        stripe_customer_id=user.user_profile.stripe_customer_id or Null,
        limits=user.user_profile.effective_limits,
        subscribed_stripe_product_ids=subscribed_stripe_product_ids,
        usage=query_user_usage(user_id),
    )
