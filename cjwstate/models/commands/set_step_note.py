from .base import BaseCommand


class SetStepNote(BaseCommand):
    def forward(self, delta):
        delta.step.notes = delta.values_for_forward["note"]
        delta.step.save(update_fields=["notes"])

    def backward(self, delta):
        delta.step.notes = delta.values_for_backward["note"]
        delta.step.save(update_fields=["notes"])

    def load_clientside_update(self, delta):
        return (
            super()
            .load_clientside_update(delta)
            .update_step(delta.step.id, notes=delta.step.notes)
        )

    def amend_create_kwargs(self, *, step, new_value, **kwargs):
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
