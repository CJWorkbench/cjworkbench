from django.db import models
from ..delta import Delta
from ..step import Step


class ChangeStepNotesCommand(Delta):
    class Meta:
        app_label = "server"
        proxy = True

    def forward(self):
        self.step.notes = self.values_for_forward["note"]
        self.step.save(update_fields=["notes"])

    def backward(self):
        self.step.notes = self.values_for_backward["note"]
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
            "values_for_backward": {"note": old_value},
            "values_for_forward": {"note": new_value},
        }
