import datetime
from typing import List, Tuple

from django.contrib.postgres.fields import ArrayField
from django.db import models

from cjwstate import clientside
from .commands import NAME_TO_COMMAND

# TODO rename database field so we can use the "datetime" module
#
# For now, we'll just pull out the one function and use that
now = datetime.datetime.now


class Delta(models.Model):
    class Meta:
        app_label = "server"
        db_table = "delta"
        ordering = ["id"]  # we read workflow.deltas.last() in tests
        constraints = [
            # Django's CharField.choices doesn't add a DB constraint. So let's
            # add one ourselves.
            models.CheckConstraint(
                check=models.Q(command_name__in=list(NAME_TO_COMMAND.keys())),
                name="delta_command_name_valid",
            ),
        ]

    # These fields must be set by any child classes, when instantiating
    workflow = models.ForeignKey(
        "Workflow", related_name="deltas", on_delete=models.CASCADE
    )

    # Next and previous Deltas on this workflow, a linked list.
    prev_delta = models.OneToOneField(
        "self",
        related_name="next_delta",
        null=True,
        default=None,
        on_delete=models.CASCADE,
    )

    datetime = models.DateTimeField("datetime", default=now)

    last_applied_at = models.DateTimeField(default=now, db_index=True)
    """Last time this Delta's result was seen -- either after Undo or for Redo.

    We delete Deltas that haven't been seen in months.

    Business logic dictates: the most-recent Delta.last_applied_at on a Workflow
    is the last Delta that was subject to do(), redo() or undo(). Deltas _after_
    that one may be older; deltas _before_ that one may be older.
    """

    command_name = models.CharField(
        choices=[(key, key) for key in NAME_TO_COMMAND.keys()],
        max_length=max(len(name) for name in NAME_TO_COMMAND.keys()),
    )

    # Foreign keys can get a bit confusing. Here we go:
    #
    # * Delta can only exist if its Step exists (Delta.step)
    # * Step depends on Workflow (Step.workflow)
    # * Delta depends on Workflow (Delta.workflow)
    #
    # So it's safe to delete Deltas from a Workflow (as long as the workflow
    # has at least one delta). But it's not safe to delete Steps from a
    # workflow -- unless one clears the Deltas first.
    #
    # We set on_delete=PROTECT because if we set on_delete=CASCADE we'd be
    # ambiguous: should one delete the Step first, or the Delta? The answer
    # is: you _must_ delete the Delta first; after deleting the Delta, you
    # _may_ delete the Step.
    #
    # TODO nix soft-deleting Tabs and Steps. Keep IDs out of the model and use
    # slugs throughout. DeleteTab.values_for_backward() would include
    # all the step data needed to recreate all deleted steps, for instance.

    tab = models.ForeignKey("Tab", null=True, on_delete=models.PROTECT)
    """Tab affected by this Delta.

    This is only set and used by some Commands.
    """

    step = models.ForeignKey("Step", null=True, on_delete=models.PROTECT)
    """Step affected by this Delta.

    This is only set and used by some Commands.
    """

    step_delta_ids = ArrayField(ArrayField(models.IntegerField(), size=2), default=list)
    """(step_id, last_relevant_delta_id) before forward() is called.

    Every Step referenced must be re-rendered when the Command's forward() is
    called. Afterwards, its last_relevant_delta_id will be self.id.
    """

    values_for_backward = models.JSONField(default=dict)
    """Data required to call .backward().

    Data format is Command-dependent.
    """

    values_for_forward = models.JSONField(default=dict)
    """Data required to call .forward().

    Data format is Command-dependent.
    """
