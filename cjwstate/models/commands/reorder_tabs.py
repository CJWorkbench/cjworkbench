from typing import List, Tuple

from django.db.models import Q

from .base import BaseCommand
from .util import ChangesStepOutputs


def _update_selected_position(workflow, from_order, to_order):
    """Write `workflow.selected_tab_position` so it points to the same tab ID.

    If `selected_tab_position` was `1` and we reordered from [A,B,C] to
    [B,C,A], then we want the new `selected_tab_position` to be `0`: that
    is, the index of B in to_ids.
    """
    old_position = workflow.selected_tab_position
    tab_id = from_order[old_position]
    new_position = to_order.index(tab_id)

    if new_position != old_position:
        workflow.selected_tab_position = new_position
        workflow.save(update_fields=["selected_tab_position"])


def _write_order(workflow, tab_ids):
    """Write `tab.position` for all tabs so they are in the given order."""
    # We validated the IDs back in `.amend_create_args()`
    for position, tab_id in enumerate(tab_ids):
        workflow.tabs.filter(pk=tab_id).update(position=position)


class ReorderTabs(ChangesStepOutputs, BaseCommand):
    """Overwrite tab.position for all tabs in a workflow."""

    def load_clientside_update(self, delta):
        return (
            super()
            .load_clientside_update(delta)
            .update_workflow(
                tab_slugs=list(delta.workflow.live_tabs.values_list("slug", flat=True))
            )
        )

    def forward(self, delta):
        _write_order(delta.workflow, delta.values_for_forward["tab_ids"])
        _update_selected_position(
            delta.workflow,
            delta.values_for_backward["tab_ids"],
            delta.values_for_forward["tab_ids"],
        )
        self.forward_affected_delta_ids(delta)

    def backward(self, delta):
        self.backward_affected_delta_ids(delta)
        _write_order(delta.workflow, delta.values_for_backward["tab_ids"])
        _update_selected_position(
            delta.workflow,
            delta.values_for_forward["tab_ids"],
            delta.values_for_backward["tab_ids"],
        )

    def affected_step_delta_ids(
        self, workflow: "Workflow", old_slugs: List[str], new_slugs: List[str]
    ) -> List[Tuple[int, int]]:
        """Find Step+Delta IDs whose output may change with this reordering.

        Reordering tabs changes the ordering of 'Multitab' params. Any Step
        with a 'Multitab' param can change as a result of this delta.

        There are very few 'Multitab' params in the wild: as of 2019-02-12, the
        only one is in "concattabs". TODO optimize this method to look one
        level deep for _only_ 'Multitab' params that depend on the changed
        ordering, not 'Tab' params, essentially making ReorderTabs _not_
        change any Steps unless there's a "concattabs" module.
        """
        # Calculate `moved_slugs`: just the slugs whose `position` changed.
        #
        # There's no need to re-render a Step that only depends on tabs
        # whose `position`s _haven't_ changed: its input tab order certainly
        # hasn't changed.
        first_change_index = None
        last_change_index = None
        for i, old_slug_and_new_slug in enumerate(zip(old_slugs, new_slugs)):
            old_slug, new_slug = old_slug_and_new_slug
            if old_slug != new_slug:
                if first_change_index is None:
                    first_change_index = i
                last_change_index = i
        moved_slugs = set(old_slugs[first_change_index : last_change_index + 1])

        # Figure out which params depend on those.
        from cjwstate.models.workflow import DependencyGraph

        graph = DependencyGraph.load_from_workflow(workflow)
        step_ids = graph.get_step_ids_depending_on_tab_slugs(moved_slugs)
        q = Q(id__in=step_ids)
        return self.q_to_step_delta_ids(q)

    def amend_create_kwargs(self, *, workflow, new_order):
        tab_slugs_and_ids = list(workflow.live_tabs.values_list("slug", "id"))
        tab_ids_by_slug = dict((t[0], t[1]) for t in tab_slugs_and_ids)
        tab_slugs_by_id = dict((t[1], t[0]) for t in tab_slugs_and_ids)

        old_order = list(workflow.live_tabs.values_list("id", flat=True))

        try:
            new_order = [tab_ids_by_slug[slug] for slug in new_order]
        except KeyError:
            raise ValueError("wrong tab slugs")
        # Need same number of elements, same elements. Don't compare sets
        # because that doesn't test number of elements.
        if sorted(new_order) != sorted(old_order):
            raise ValueError("wrong tab slugs")

        if new_order == old_order:
            return None

        old_slugs = [tab_slugs_by_id[id] for id in old_order]
        new_slugs = [tab_slugs_by_id[id] for id in new_order]
        step_delta_ids = self.affected_step_delta_ids(workflow, old_slugs, new_slugs)

        return {
            "workflow": workflow,
            "values_for_backward": {"tab_ids": old_order},
            "values_for_forward": {"tab_ids": new_order},
            "step_delta_ids": step_delta_ids,
        }
