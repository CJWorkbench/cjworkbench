from django.db import models
from cjwstate.models import Delta, Tab
from .util import ChangesStepOutputs


class SetTabNameCommand(ChangesStepOutputs, Delta):
    """
    Set a tab name.

    This changes Step outputs if any module has a 'tab' parameter that
    refers to this tab: the 'tab' parameter data includes tab _name_.
    """

    class Meta:
        app_label = "server"
        proxy = True

    # override
    def load_clientside_update(self):
        return (
            super()
            .load_clientside_update()
            .update_tab(self.tab.slug, name=self.tab.name)
        )

    def forward(self):
        self.tab.name = self.values_for_forward["name"]
        self.tab.save(update_fields=["name"])
        self.forward_affected_delta_ids()

    def backward(self):
        self.backward_affected_delta_ids()
        self.tab.name = self.values_for_backward["name"]
        self.tab.save(update_fields=["name"])

    @classmethod
    def amend_create_kwargs(cls, *, workflow, tab, new_name):
        if tab.name == new_name:
            return None

        # step_delta_ids includes:
        #
        # * All modules in this tab (because render() may have tab_name arg)
        # * All modules in dependent tabs (because 'tab' param value changes)
        in_tab_q = models.Q(tab_id=tab.id, is_deleted=False)
        from_tab_q = cls.affected_steps_from_tab(tab)
        q = in_tab_q | from_tab_q
        step_delta_ids = cls.q_to_step_delta_ids(q)

        return {
            "workflow": workflow,
            "tab": tab,
            "values_for_backward": {"name": tab.name},
            "values_for_forward": {"name": new_name},
            "step_delta_ids": step_delta_ids,
        }
