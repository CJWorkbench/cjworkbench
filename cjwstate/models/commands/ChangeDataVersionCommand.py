from django.db import models
from cjwstate.models import Delta, WfModule
from .util import ChangesWfModuleOutputs


class ChangeDataVersionCommand(ChangesWfModuleOutputs, Delta):
    class Meta:
        app_label = "server"
        db_table = "server_changedataversioncommand"

    wf_module = models.ForeignKey(WfModule, on_delete=models.PROTECT)
    # may not have had a previous version
    old_version = models.DateTimeField("old_version", null=True)
    new_version = models.DateTimeField("new_version")
    wf_module_delta_ids = ChangesWfModuleOutputs.wf_module_delta_ids

    def forward(self):
        self.wf_module.stored_data_version = self.new_version
        self.wf_module.save(update_fields=["stored_data_version"])
        self.forward_affected_delta_ids()

    def backward(self):
        self.wf_module.stored_data_version = self.old_version
        self.wf_module.save(update_fields=["stored_data_version"])
        self.backward_affected_delta_ids()

    # override
    def get_modifies_render_output(self) -> bool:
        """
        Tell renderers to render the new workflow, _maybe_.
        """
        return True

    @classmethod
    def amend_create_kwargs(cls, *, wf_module, **kwargs):
        return {
            **kwargs,
            "wf_module": wf_module,
            "old_version": wf_module.stored_data_version,
            "wf_module_delta_ids": cls.affected_wf_module_delta_ids(wf_module),
        }

    @property
    def command_description(self):
        return (
            f"Change WfModule[{self.wf_module_id}] data version to "
            f"{self.new_version}"
        )
