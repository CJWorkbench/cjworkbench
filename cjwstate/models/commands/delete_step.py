from django.db.models import F, Q

from cjwstate import clientside
from ..dbutil import make_gap_in_list, remove_gap_from_list
from .base import BaseCommand
from .util import ChangesStepOutputs


class DeleteStep(ChangesStepOutputs, BaseCommand):
    """Remove `step` from its Workflow.

    Our logic is to "soft-delete": set `step.is_deleted=True`. Most facets
    of Workbench's API should pretend a soft-deleted Step does not exist.
    """

    def load_clientside_update(self, delta):
        ret = (
            super()
            .load_clientside_update(delta)
            .update_tab(
                delta.step.tab_slug,
                step_ids=list(delta.step.tab.live_steps.values_list("id", flat=True)),
            )
        )
        blocks = delta.values_for_backward.get("blocks", [])
        if blocks:
            ret = ret.update_workflow(
                block_slugs=list(delta.workflow.blocks.values_list("slug", flat=True))
            )
            if delta.step.is_deleted:
                # Clear the blocks we deleted
                ret = ret.clear_blocks(block["slug"] for block in blocks)
            else:
                # Undoing, we need to re-add slugs
                ret = ret.replace_blocks(
                    {
                        block["slug"]: clientside.ChartBlock(delta.step.slug)
                        for block in blocks
                    }
                )
        return ret

    def affected_steps_in_tab(self, step) -> Q:
        # We don't need to change step's delta_id: just the others.
        return Q(tab_id=step.tab_id, order__gt=step.order, is_deleted=False)

    def forward(self, delta):
        # If we are deleting the selected module, then set the previous module
        # in stack as selected (behavior same as in workflow-reducer.js)
        tab = delta.step.tab
        selected = tab.selected_step_position
        if selected is not None and selected >= delta.step.order:
            selected -= 1
            if selected >= 0:
                tab.selected_step_position = selected
            else:
                tab.selected_step_position = None
            tab.save(update_fields=["selected_step_position"])

        # Delete charts from the report
        blocks = list(delta.step.blocks.all())
        delta.step.blocks.all().delete()
        for block in reversed(blocks):
            remove_gap_from_list(delta.workflow.blocks, "position", block.position)

        # Soft-delete the step
        # Also, ensure auto_update_data=False so Undo won't add auto-update
        # (If we didn't do this, Undo might help a user exceed his/her limit.)
        delta.step.is_deleted = True
        delta.step.auto_update_data = False
        delta.step.next_update = None
        delta.step.save(update_fields=["is_deleted", "auto_update_data", "next_update"])
        tab.live_steps.filter(order__gt=delta.step.order).update(order=F("order") - 1)

        delta.workflow.recalculate_fetches_per_day()
        delta.workflow.save(update_fields=["fetches_per_day"])

        self.forward_affected_delta_ids(delta)

    def backward(self, delta):
        tab = delta.step.tab

        # Move subsequent modules over to make way for this one.
        tab.live_steps.filter(order__gte=delta.step.order).update(order=F("order") + 1)

        delta.step.is_deleted = False
        delta.step.save(update_fields=["is_deleted"])

        blocks = delta.values_for_backward.get("blocks", [])
        for block_kwargs in blocks:
            make_gap_in_list(
                delta.workflow.blocks, "position", block_kwargs["position"]
            )
            delta.workflow.blocks.create(**block_kwargs, step_id=delta.step_id)

        # Don't set tab.selected_step_position. We can't restore it, and
        # this operation can't invalidate any value that was there previously.

        self.backward_affected_delta_ids(delta)

    def amend_create_kwargs(self, *, workflow, step, **kwargs):
        # If step is already deleted, ignore this Delta.
        #
        # This works around a race: what if two users delete the same Step
        # at the same time? We want only one Delta to be created.
        # amend_create_kwargs() is called within workflow.cooperative_lock(),
        # so we can check without racing whether step is already deleted.
        step.refresh_from_db()
        if step.is_deleted or step.tab.is_deleted:
            return None

        values_for_backward = {}
        if workflow.has_custom_report:
            values_for_backward["blocks"] = list(
                {
                    k: v
                    for k, v in block.to_json_safe_kwargs().items()
                    if k != "step_slug"
                }
                for block in step.blocks.all()
            )

        return {
            **kwargs,
            "workflow": workflow,
            "step": step,
            "step_delta_ids": self.affected_step_delta_ids(step),
            "values_for_backward": values_for_backward,
        }


# You may be wondering why there's no @receiver(pre_delete, ...) here. That's
# because if we're deleting a DeleteStep command, then that means _previous_
# Deltas assume the Step exists. We must always delete Deltas in reverse order,
# from most-recent to least-recent. Only AddStep deletion should delete a Step.
#
# Don't delete the Step here. That would break every other Delta.
