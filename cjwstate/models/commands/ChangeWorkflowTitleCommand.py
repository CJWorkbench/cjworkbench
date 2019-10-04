from django.db import models
from cjwstate.models import Delta


class ChangeWorkflowTitleCommand(Delta):
    class Meta:
        app_label = "server"
        db_table = "server_changeworkflowtitlecommand"

    new_value = models.TextField("new_value")
    old_value = models.TextField("old_value")

    def forward(self):
        self.workflow.name = self.new_value
        self.workflow.save(update_fields=["name"])

    def backward(self):
        self.workflow.name = self.old_value
        self.workflow.save(update_fields=["name"])

    @classmethod
    def amend_create_kwargs(cls, *, workflow, new_value, **kwargs):
        return {
            **kwargs,
            "workflow": workflow,
            "old_value": workflow.name,
            "new_value": new_value,
        }

    @property
    def command_description(self):
        return f"Change workflow name to {self.new_value}"
