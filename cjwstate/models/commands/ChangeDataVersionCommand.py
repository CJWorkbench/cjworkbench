from django.db import models
from ..delta import Delta
from ..step import Step
from .util import ChangesStepOutputs


class ChangeDataVersionCommand(ChangesStepOutputs, Delta):
    class Meta:
        app_label = "server"
        db_table = "server_changedataversioncommand"

    step = models.ForeignKey(Step, on_delete=models.PROTECT)
    # may not have had a previous version
    old_version = models.DateTimeField("old_version", null=True)
    new_version = models.DateTimeField("new_version")
    step_delta_ids = ChangesStepOutputs.step_delta_ids

    def forward(self):
        self.step.stored_data_version = self.new_version
        self.step.save(update_fields=["stored_data_version"])
        self.forward_affected_delta_ids()

    def backward(self):
        self.step.stored_data_version = self.old_version
        self.step.save(update_fields=["stored_data_version"])
        self.backward_affected_delta_ids()

    # override
    def get_modifies_render_output(self) -> bool:
        """Tell renderers to render the new workflow, _maybe_."""
        return True

    @classmethod
    def amend_create_kwargs(cls, *, step, **kwargs):
        return {
            **kwargs,
            "step": step,
            "old_version": step.stored_data_version,
            "step_delta_ids": cls.affected_step_delta_ids(step),
        }

    @property
    def command_description(self):
        return f"Change Step[{self.step_id}] data version to {self.new_version}"
