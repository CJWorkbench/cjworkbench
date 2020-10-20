from django.db import models
from django.db.models import F
from ..delta import Delta
from ..step import Step
from .util import ChangesStepOutputs


class DeleteModuleCommand(ChangesStepOutputs, Delta):
    """
    Remove `step` from its Workflow.

    Our logic is to "soft-delete": set `step.is_deleted=True`. Most facets
    of Workbench's API should pretend a soft-deleted Step does not exist.
    """

    class Meta:
        app_label = "server"
        proxy = True

    # override
    def load_clientside_update(self):
        return (
            super()
            .load_clientside_update()
            .update_tab(
                self.step.tab_slug,
                step_ids=list(self.step.tab.live_steps.values_list("id", flat=True)),
            )
        )

    @classmethod
    def affected_steps_in_tab(cls, step) -> models.Q:
        # We don't need to change self.step's delta_id: just the others.
        return models.Q(tab_id=step.tab_id, order__gt=step.order, is_deleted=False)

    def forward(self):
        # If we are deleting the selected module, then set the previous module
        # in stack as selected (behavior same as in workflow-reducer.js)
        tab = self.step.tab
        selected = tab.selected_step_position
        if selected is not None and selected >= self.step.order:
            selected -= 1
            if selected >= 0:
                tab.selected_step_position = selected
            else:
                tab.selected_step_position = None
            tab.save(update_fields=["selected_step_position"])

        self.step.is_deleted = True
        self.step.save(update_fields=["is_deleted"])

        tab.live_steps.filter(order__gt=self.step.order).update(order=F("order") - 1)

        self.forward_affected_delta_ids()

    def backward(self):
        tab = self.step.tab

        # Move subsequent modules over to make way for this one.
        tab.live_steps.filter(order__gte=self.step.order).update(order=F("order") + 1)

        self.step.is_deleted = False
        self.step.save(update_fields=["is_deleted"])

        # Don't set tab.selected_step_position. We can't restore it, and
        # this operation can't invalidate any value that was there previously.

        self.backward_affected_delta_ids()

    @classmethod
    def amend_create_kwargs(cls, *, step, **kwargs):
        # If step is already deleted, ignore this Delta.
        #
        # This works around a race: what if two users delete the same Step
        # at the same time? We want only one Delta to be created.
        # amend_create_kwargs() is called within workflow.cooperative_lock(),
        # so we can check without racing whether step is already deleted.
        step.refresh_from_db()
        if step.is_deleted or step.tab.is_deleted:
            return None

        return {
            **kwargs,
            "step": step,
            "step_delta_ids": cls.affected_step_delta_ids(step),
        }


# You may be wondering why there's no @receiver(pre_delete, ...) here. That's
# because if we're deleting a DeleteModuleCommand, then that means _previous_
# Deltas assume the Step exists. We must always delete Deltas in reverse order,
# from most-recent to least-recent. Only AddModuleCommand should delete a Step.
#
# Don't delete the Step here. That would break every other Delta.
