from django.db import models
from cjwstate.models import Delta, WfModule


class ChangeWfModuleNotesCommand(Delta):
    class Meta:
        app_label = "server"
        db_table = "server_changewfmodulenotescommand"

    wf_module = models.ForeignKey(WfModule, on_delete=models.PROTECT)
    new_value = models.TextField("new_value")
    old_value = models.TextField("old_value")

    def forward(self):
        self.wf_module.notes = self.new_value
        self.wf_module.save(update_fields=["notes"])

    def backward(self):
        self.wf_module.notes = self.old_value
        self.wf_module.save(update_fields=["notes"])

    # override
    def load_clientside_update(self):
        return (
            super()
            .load_clientside_update()
            .update_step(self.wf_module.id, notes=self.wf_module.notes)
        )

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
