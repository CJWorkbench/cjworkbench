from django.db import models
from server.models import Delta, Tab
from .util import ChangesWfModuleOutputs


class SetTabNameCommand(ChangesWfModuleOutputs, Delta):
    """
    Set a tab name.

    This changes WfModule outputs if any module has a 'tab' parameter that
    refers to this tab: the 'tab' parameter data includes tab _name_.
    """

    tab = models.ForeignKey(Tab, on_delete=models.PROTECT)
    old_name = models.TextField()
    new_name = models.TextField()
    wf_module_delta_ids = ChangesWfModuleOutputs.wf_module_delta_ids

    def load_ws_data(self):
        data = super().load_ws_data()
        data["updateTabs"] = {self.tab.slug: {"name": self.tab.name}}
        return data

    def forward_impl(self):
        self.tab.name = self.new_name
        self.tab.save(update_fields=["name"])
        self.forward_affected_delta_ids()

    def backward_impl(self):
        self.backward_affected_delta_ids()
        self.tab.name = self.old_name
        self.tab.save(update_fields=["name"])

    @classmethod
    def amend_create_kwargs(cls, *, workflow, tab, new_name):
        if tab.name == new_name:
            return None

        # wf_module_delta_ids includes:
        #
        # * All modules in this tab (because render() may have tab_name arg)
        # * All modules in dependent tabs (because 'tab' param value changes)
        in_tab_q = models.Q(tab_id=tab.id, is_deleted=False)
        from_tab_q = cls.affected_wf_modules_from_tab(tab)
        q = in_tab_q | from_tab_q
        wf_module_delta_ids = cls.q_to_wf_module_delta_ids(q)

        return {
            "workflow": workflow,
            "tab": tab,
            "new_name": new_name,
            "old_name": tab.name,
            "wf_module_delta_ids": wf_module_delta_ids,
        }
