from django.db.models import Q

from .base import BaseCommand
from .util import ChangesStepOutputs


class SetTabName(ChangesStepOutputs, BaseCommand):
    """Set a tab name.

    This changes Step outputs if any module has a 'tab' parameter that
    refers to this tab: the 'tab' parameter data includes tab _name_.
    """

    def load_clientside_update(self, delta):
        return (
            super()
            .load_clientside_update(delta)
            .update_tab(delta.tab.slug, name=delta.tab.name)
        )

    def forward(self, delta):
        delta.tab.name = delta.values_for_forward["name"]
        delta.tab.save(update_fields=["name"])
        self.forward_affected_delta_ids(delta)

    def backward(self, delta):
        self.backward_affected_delta_ids(delta)
        delta.tab.name = delta.values_for_backward["name"]
        delta.tab.save(update_fields=["name"])

    def amend_create_kwargs(self, *, workflow, tab, new_name):
        if tab.name == new_name:
            return None

        # step_delta_ids includes:
        #
        # * All modules in this tab (because render() may have tab_name arg)
        # * All modules in dependent tabs (because 'tab' param value changes)
        in_tab_q = Q(tab_id=tab.id, is_deleted=False)
        from_tab_q = self.affected_steps_from_tab(tab)
        q = in_tab_q | from_tab_q
        step_delta_ids = self.q_to_step_delta_ids(q)

        return {
            "workflow": workflow,
            "tab": tab,
            "values_for_backward": {"name": tab.name},
            "values_for_forward": {"name": new_name},
            "step_delta_ids": step_delta_ids,
        }
