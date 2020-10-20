from django.db import models
from cjwstate.models import Delta


class ChangeWorkflowTitleCommand(Delta):
    class Meta:
        app_label = "server"
        proxy = True

    def forward(self):
        self.workflow.name = self.values_for_forward["title"]
        self.workflow.save(update_fields=["name"])

    def backward(self):
        self.workflow.name = self.values_for_backward["title"]
        self.workflow.save(update_fields=["name"])

    # override
    def load_clientside_update(self):
        return super().load_clientside_update().update_workflow(name=self.workflow.name)

    @classmethod
    def amend_create_kwargs(cls, *, workflow, new_value, **kwargs):
        return {
            **kwargs,
            "workflow": workflow,
            "values_for_backward": {"title": workflow.name},
            "values_for_forward": {"title": new_value},
        }
