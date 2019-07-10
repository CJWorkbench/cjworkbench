from django.db import models
from server.models import Delta, WfModule


class ChangeWfModuleNotesCommand(Delta):
    wf_module = models.ForeignKey(WfModule, on_delete=models.PROTECT)
    new_value = models.TextField("new_value")
    old_value = models.TextField("old_value")

    def forward_impl(self):
        self.wf_module.notes = self.new_value
        self.wf_module.save(update_fields=["notes"])

    def backward_impl(self):
        self.wf_module.notes = self.old_value
        self.wf_module.save(update_fields=["notes"])

    # override
    def load_ws_data(self):
        wf_module = self.wf_module
        return {
            "updateWorkflow": self._load_workflow_ws_data(),
            "updateWfModules": {str(wf_module.id): {"notes": wf_module.notes}},
        }

    @classmethod
    def amend_create_kwargs(cls, *, wf_module, new_value, **kwargs):
        wf_module.refresh_from_db()  # now that we're atomic

        old_value = wf_module.notes or ""
        if new_value == old_value:
            return None

        return {
            **kwargs,
            "wf_module": wf_module,
            "old_value": old_value,
            "new_value": new_value,
        }

    @property
    def command_description(self):
        return f"Change WfModule note to {self.new_value}"
