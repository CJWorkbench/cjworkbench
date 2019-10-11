from typing import List, Tuple
from django.contrib.postgres.fields import ArrayField
from django.db import models
from cjwstate.models import Delta, Workflow
from cjwstate.models.workflow import DependencyGraph
from .util import ChangesWfModuleOutputs


class ReorderTabsCommand(ChangesWfModuleOutputs, Delta):
    """Overwrite tab.position for all tabs in a workflow."""

    class Meta:
        app_label = "server"
        db_table = "server_reordertabscommand"

    old_order = ArrayField(models.IntegerField())
    new_order = ArrayField(models.IntegerField())
    wf_module_delta_ids = ChangesWfModuleOutputs.wf_module_delta_ids

    def load_ws_data(self):
        data = super().load_ws_data()
        data["updateWorkflow"]["tab_slugs"] = list(
            self.workflow.live_tabs.values_list("slug", flat=True)
        )
        return data

    def _write_order(self, tab_ids):
        """Write `tab.position` for all tabs so they are in the given order."""
        # We validated the IDs back in `.amend_create_args()`
        for position, tab_id in enumerate(tab_ids):
            self.workflow.tabs.filter(pk=tab_id).update(position=position)

    def _update_selected_position(self, from_order, to_order):
        """
        Write `workflow.selected_tab_position` so it points to the same tab ID.

        If `selected_tab_position` was `1` and we reordered from [A,B,C] to
        [B,C,A], then we want the new `selected_tab_position` to be `0`: that
        is, the index of B in to_ids.
        """
        old_position = self.workflow.selected_tab_position
        tab_id = from_order[old_position]
        new_position = to_order.index(tab_id)

        if new_position != old_position:
            self.workflow.selected_tab_position = new_position
            self.workflow.save(update_fields=["selected_tab_position"])

    def forward(self):
        self._write_order(self.new_order)
        self._update_selected_position(self.old_order, self.new_order)
        self.forward_affected_delta_ids()

    def backward(self):
        self.backward_affected_delta_ids()
        self._write_order(self.old_order)
        self._update_selected_position(self.new_order, self.old_order)

    @classmethod
    def affected_wf_module_delta_ids(
        cls, workflow: Workflow, old_slugs: List[str], new_slugs: List[str]
    ) -> List[Tuple[int, int]]:
        """
        Find WfModule+Delta IDs whose output may change with this reordering.

        Reordering tabs changes the ordering of 'Multitab' params. Any WfModule
        with a 'Multitab' param can change as a result of this delta.

        There are very few 'Multitab' params in the wild: as of 2019-02-12, the
        only one is in "concattabs". TODO optimize this method to look one
        level deep for _only_ 'Multitab' params that depend on the changed
        ordering, not 'Tab' params, essentially making ReorderTabsCommand _not_
        change any WfModules unless there's a "concattabs" module.
        """
        # Calculate `moved_slugs`: just the slugs whose `position` changed.
        #
        # There's no need to re-render a WfModule that only depends on tabs
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
        graph = DependencyGraph.load_from_workflow(workflow)
        wf_module_ids = graph.get_step_ids_depending_on_tab_slugs(moved_slugs)
        q = models.Q(id__in=wf_module_ids)
        return cls.q_to_wf_module_delta_ids(q)

    @classmethod
    def amend_create_kwargs(cls, *, workflow, new_order):
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
        wf_module_delta_ids = cls.affected_wf_module_delta_ids(
            workflow, old_slugs, new_slugs
        )

        return {
            "workflow": workflow,
            "new_order": new_order,
            "old_order": old_order,
            "wf_module_delta_ids": wf_module_delta_ids,
        }
