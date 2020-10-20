import json
from django.db import models
from cjwstate.models import Delta
from .util import ChangesStepOutputs


class ReorderModulesCommand(ChangesStepOutputs, Delta):
    """Overwrite step.order for all steps in a tab."""

    class Meta:
        app_label = "server"
        proxy = True

    # override
    def load_clientside_update(self):
        return (
            super()
            .load_clientside_update()
            .update_tab(
                self.tab.slug,
                step_ids=list(self.tab.live_steps.values_list("id", flat=True)),
            )
        )

    def apply_order(self, order):
        # We validated Step IDs back in `.amend_create_args()`
        for record in order:
            self.tab.steps.filter(pk=record["id"]).update(order=record["order"])

    def forward(self):
        self.apply_order(self.values_for_forward["legacy_format"])
        self.forward_affected_delta_ids()

    def backward(self):
        self.apply_order(self.values_for_backward["legacy_format"])
        self.backward_affected_delta_ids()

    @classmethod
    def amend_create_kwargs(cls, *, workflow, tab, new_order, **kwargs):
        old_order = tab.live_steps.values_list("id", flat=True)

        try:
            if sorted(new_order) != sorted(old_order):
                raise ValueError("new_order does not have the expected elements")
        except NameError:
            raise ValueError("new_order is not a list of numbers")

        # Find first _order_ that gets a new Step. Only this and subsequent
        # Steps will produce new output
        for position in range(len(new_order)):
            if new_order[position] != old_order[position]:
                min_diff_order = position
                break
        else:
            # Nothing was reordered; don't create this Command.
            return None

        # Now write an icky JSON format instead of our nice lists
        # TODO store arrays of slugs
        old_order_dicts = [
            {"id": id, "order": order} for order, id in enumerate(old_order)
        ]
        new_order_dicts = [
            {"id": id, "order": order} for order, id in enumerate(new_order)
        ]

        # step_delta_ids of affected Steps will be all modules in the
        # database _before update_, starting at `order=min_diff_order`.
        #
        # This list of Step IDs will be the same (in a different order --
        # order doesn't matter) _after_ update.
        step = tab.live_steps.get(order=min_diff_order)
        step_delta_ids = cls.affected_step_delta_ids(step)

        return {
            **kwargs,
            "workflow": workflow,
            "tab": tab,
            "values_for_backward": {"legacy_format": old_order_dicts},
            "values_for_forward": {"legacy_format": new_order_dicts},
            "step_delta_ids": step_delta_ids,
        }
