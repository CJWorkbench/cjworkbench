from .base import BaseCommand


class SetWorkflowTitle(BaseCommand):
    def forward(self, delta):
        delta.workflow.name = delta.values_for_forward["title"]
        delta.workflow.save(update_fields=["name"])

    def backward(self, delta):
        delta.workflow.name = delta.values_for_backward["title"]
        delta.workflow.save(update_fields=["name"])

    def load_clientside_update(self, delta):
        return (
            super()
            .load_clientside_update(delta)
            .update_workflow(name=delta.workflow.name)
        )

    def amend_create_kwargs(delta, *, workflow, new_value, **kwargs):
        return {
            **kwargs,
            "workflow": workflow,
            "values_for_backward": {"title": workflow.name},
            "values_for_forward": {"title": new_value},
        }
