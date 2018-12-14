from django.contrib.postgres.fields import ArrayField
from django.db import models
from server.models import Delta


class ReorderTabsCommand(Delta):
    """Overwrite tab.position for all tabs in a workflow."""

    old_order = ArrayField(models.IntegerField())
    new_order = ArrayField(models.IntegerField())

    def load_ws_data(self):
        data = super().load_ws_data()
        data['updateWorkflow']['tab_ids'] = list(
            self.workflow.live_tabs.values_list('id', flat=True)
        )
        return data

    def _write_order(self, tab_ids):
        """Write `tab.position` for all tabs so they are in the given order."""
        # We validated the IDs back in `.amend_create_args()`
        for position, tab_id in enumerate(tab_ids):
            self.workflow.tabs \
                .filter(pk=tab_id) \
                .update(position=position)

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
            self.workflow.save(update_fields=['selected_tab_position'])

    def forward_impl(self):
        self._write_order(self.new_order)
        self._update_selected_position(self.old_order, self.new_order)

    def backward_impl(self):
        self._write_order(self.old_order)
        self._update_selected_position(self.new_order, self.old_order)

    async def schedule_execute(self):
        pass

    @classmethod
    def amend_create_kwargs(cls, *, workflow, new_order):
        old_order = list(workflow.live_tabs.values_list('id', flat=True))

        if sorted(new_order) != sorted(old_order):
            raise ValueError('wrong tab IDs')

        if new_order == old_order:
            return None

        return {
            'workflow': workflow,
            'new_order': new_order,
            'old_order': old_order,
        }
