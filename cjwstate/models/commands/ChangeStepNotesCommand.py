from django.db import models
from ..delta import Delta
from ..step import Step


class ChangeStepNotesCommand(Delta):
    class Meta:
        app_label = "server"
        db_table = "server_changestepnotescommand"

    step = models.ForeignKey(Step, on_delete=models.PROTECT)
    new_value = models.TextField("new_value")
    old_value = models.TextField("old_value")

    def forward(self):
        self.step.notes = self.new_value
        self.step.save(update_fields=["notes"])

    def backward(self):
        self.step.notes = self.old_value
        self.step.save(update_fields=["notes"])

    # override
    def load_clientside_update(self):
        return (
            super()
            .load_clientside_update()
            .update_step(self.step.id, notes=self.step.notes)
        )

    @classmethod
    def amend_create_kwargs(cls, *, step, new_value, **kwargs):
        step.refresh_from_db()  # now that we're atomic

        old_value = step.notes or ""
        if new_value == old_value:
            return None

        return {
            **kwargs,
            "step": step,
            "old_value": old_value,
            "new_value": new_value,
        }

    @property
    def command_description(self):
        return f"Change Step note to {self.new_value}"
