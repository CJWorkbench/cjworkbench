from typing import List, Tuple

import django.utils
from django.contrib.postgres.fields import ArrayField, JSONField
from django.db import connection, models
from polymorphic.models import PolymorphicModel

from cjwstate import clientside


# Base class of a single undoable/redoable action
# Derived classes implement the actual mutations on the database
# (via polymorphic forward()/backward())
# To derive a command from Delta:
#
#   - implement @classmethod amend_create_kwargs() -- a database-sync method.
#   - implement load_clientside_update() -- a database-sync method.
#   - implement forward() and backward() -- database-sync methods.
#
# Create Deltas using `cjwstate.commands.do()`. This will call these
# synchronous methods correctly.
class Delta(PolymorphicModel):
    class Meta:
        app_label = "server"
        db_table = "delta"

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

    datetime = models.DateTimeField("datetime", default=django.utils.timezone.now)

    # Foreign keys can get a bit confusing. Here we go:
    #
    # * AddModuleCommand can only exist if its Step exists (Delta.step)
    # * Step depends on Workflow (Step.workflow)
    # * AddModuleCommand depends on Workflow (Delta.workflow)
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
    # slugs throughout. DeleteTabCommand.values_for_backward() would include
    # all the step data needed to recreate all deleted steps, for instance.

    tab = models.ForeignKey("Tab", null=True, on_delete=models.PROTECT)
    """Tab affected by this Delta.

    This is only set and used by some subclasses.
    """

    step = models.ForeignKey("Step", null=True, on_delete=models.PROTECT)
    """Step affected by this Delta.

    This is only set and used by some subclasses.
    """

    step_delta_ids = ArrayField(ArrayField(models.IntegerField(), size=2), default=list)
    """(step_id, last_relevant_delta_id) before forward() is called.

    Every Step referenced must be re-rendered when this step's forward() is
    called. Afterwards, its last_relevant_delta_id will be self.id.
    """

    values_for_backward = JSONField(default=dict)
    """Data required to call .backward().

    Data format is subclass-dependent.
    """

    values_for_forward = JSONField(default=dict)
    """Data required to call .forward().

    Data format is subclass-dependent.
    """

    def load_clientside_update(self) -> clientside.Update:
        """Build state updates for the client to receive over Websockets.

        This is called synchronously. It may access the database. When
        overriding, be sure to call super() to update the most basic data.

        This must be called in a `workflow.cooperative_lock()`.
        """
        return clientside.Update(
            workflow=clientside.WorkflowUpdate(
                # self.workflow.last_delta may not be `self`
                updated_at=self.workflow.last_delta.datetime
            )
        )

    def get_modifies_render_output(self) -> bool:
        """Return whether this Delta might change a Step's render() output.

        This must be called in a `workflow.cooperative_lock()`.
        """
        return False

    @classmethod
    def affected_step_delta_ids(cls, step: "Step") -> List[Tuple[int, int]]:
        """Calculate [(step_id, previous_delta_id)] for `step` and deps.

        This is a stub. Subclass ChangesStepOutputs (and read this method's
        documentation there) if you are creating a Delta that may require a
        render.
        """
        return []

    @classmethod
    def amend_create_kwargs(cls, **kwargs):
        """Look up additional objects.create() kwargs from the database.

        Delta creation can depend upon values already in the database. The
        delta may calculate those values itself.

        Return `None` to abort creating the Delta altogether.

        Example:

            @classmethod
            def amend_create_kwargs(cls, *, workflow, **kwargs):
                return {**kwargs, 'workflow': workflow, 'old_value': ... }
        """
        return kwargs

    def delete_with_successors(self):
        """Delete all Deltas in self.workflow, starting with this one.

        Do it in SQL, not code: there can be thousands, and Django's models are
        resource-intensive. (Also, recursion is out of the question, in these
        quantities.)

        Assumes a Delta with a higher ID is a successor.

        Consider calling `workflow.delete_orphan_soft_deleted_models()` after
        calling this method: it may leave behind Tab and Step objects that
        nothing refers to, if they previously had `.is_deleted == True`.
        """
        Delta.objects.filter(workflow_id=self.workflow_id, id__gte=self.id).delete()
