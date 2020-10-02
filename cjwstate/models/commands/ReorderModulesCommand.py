import json
from django.db import models
from cjwstate.models import Delta
from .util import ChangesStepOutputs


class ReorderModulesCommand(ChangesStepOutputs, Delta):
    """Overwrite step.order for all steps in a tab."""

    class Meta:
        app_label = "server"
        db_table = "server_reordermodulescommand"

    tab = models.ForeignKey("Tab", on_delete=models.PROTECT)
    # We use a bizarre legacy data format: JSON [ { id: x, order: y}, ... ]
    old_order = models.TextField()
    new_order = models.TextField()
    step_delta_ids = ChangesStepOutputs.step_delta_ids

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
        # We validated Workflow IDs back in `.amend_create_args()`
        for record in order:
            self.tab.steps.filter(pk=record["id"]).update(order=record["order"])

    def forward(self):
        new_order = json.loads(self.new_order)
        self.apply_order(new_order)

        self.forward_affected_delta_ids()

    def backward(self):
        old_order = json.loads(self.old_order)
        self.apply_order(old_order)

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
        # TODO simply write arrays to the database.
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
            "old_order": json.dumps(old_order_dicts),
            "new_order": json.dumps(new_order_dicts),
            "step_delta_ids": step_delta_ids,
        }

    @property
    def command_description(self):
        return f"Reorder modules to {self.new_order}"
