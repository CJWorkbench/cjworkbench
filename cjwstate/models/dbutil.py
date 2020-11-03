from typing import List

from django.db.models import F, QuerySet


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
