from typing import Any, Dict, List
from .base import BaseCommand
from .util import ChangesStepOutputs


def _apply_order(tab, slugs):
    # We validated Step IDs back in `.amend_create_args()`
    for position, slug in enumerate(slugs):
        tab.live_steps.filter(slug=slug).update(order=position)


def _delta_values_to_slugs(tab, values: Dict[str, Any]) -> List[str]:
    """Find the desired order of slugs from delta.values_for_whatever.

    This handles "old-style" formats:

        {
            "legacy_format": [
                {"id": 123, "order": 0},
                {"id": 234, "order": 1},
                ...
            ]
        }

    (list generated with code:
    `[{"id": id, "order": order} for order, id in enumerate(old_order)]`)

    And the "new-style" format [2020-11-23]:

        {
            "slugs": ["step-2", "step-1", ...]
        }

    (The "new-style" format ignores step IDs, so it can refer to deleted-then-
    undeleted steps. [These don't exist as of 2020-11-23.])
    """
    if "legacy_format" in values:
        id_to_slug = {id: slug for id, slug in tab.live_steps.values_list("id", "slug")}
        ordered_ids = [
            v["id"] for v in sorted(values["legacy_format"], key=lambda v: v["order"])
        ]
        return [id_to_slug[id] for id in ordered_ids]
    else:
        return values["slugs"]


class ReorderSteps(ChangesStepOutputs, BaseCommand):
    """Overwrite step.order for all steps in a tab."""

    def load_clientside_update(self, delta):
        return (
            super()
            .load_clientside_update(delta)
            .update_tab(
                delta.tab.slug,
                step_ids=list(delta.tab.live_steps.values_list("id", flat=True)),
            )
        )

    def forward(self, delta):
        slugs = _delta_values_to_slugs(delta.tab, delta.values_for_forward)
        _apply_order(delta.tab, slugs)
        self.forward_affected_delta_ids(delta)

    def backward(self, delta):
        slugs = _delta_values_to_slugs(delta.tab, delta.values_for_backward)
        _apply_order(delta.tab, slugs)
        self.backward_affected_delta_ids(delta)

    def amend_create_kwargs(self, *, workflow, tab, slugs, **kwargs):
        old_slugs = list(tab.live_steps.values_list("slug", flat=True))

        if sorted(slugs) != sorted(old_slugs):
            raise ValueError("slugs does not have the expected elements")

        # Find first _order_ that gets a new Step. Only this and subsequent
        # Steps will produce new output
        for position, (new_slug, old_slug) in enumerate(zip(slugs, old_slugs)):
            if old_slug != new_slug:
                min_diff_order = position
                break
        else:
            # Nothing was reordered; don't create this Command.
            return None

        # step_delta_ids of affected Steps will be all modules in the
        # database _before update_, starting at `order=min_diff_order`.
        #
        # This list of Step IDs will be the same (in a different order --
        # order doesn't matter) _after_ update.
        step = tab.live_steps.get(order=min_diff_order)
        step_delta_ids = self.affected_step_delta_ids(step)

        return {
            **kwargs,
            "workflow": workflow,
            "tab": tab,
            "values_for_backward": {"slugs": old_slugs},
            "values_for_forward": {"slugs": slugs},
            "step_delta_ids": step_delta_ids,
        }
