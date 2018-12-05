from django.db import models
from .Workflow import Workflow


class Tab(models.Model):
    """A sequence of WfModules in a Workflow."""
    class Meta:
        ordering = ['position']

    workflow = models.ForeignKey(Workflow, related_name='tabs',
                                 on_delete=models.CASCADE)
    name = models.TextField()
    position = models.IntegerField()
    selected_wf_module_position = models.IntegerField(null=True)
    is_deleted = models.BooleanField(default=False)

    @property
    def live_wf_modules(self):
        return self.wf_modules.filter(is_deleted=False)

    def duplicate(self, to_workflow: Workflow) -> None:
        """Deep-copy this Tab to a new Tab in `to_workflow`."""

        new_tab = to_workflow.tabs.create(
            name=self.name,
            position=self.position,
            selected_wf_module_position=self.selected_wf_module_position,
        )
        wf_modules = list(self.live_wf_modules)
        for wf_module in wf_modules:
            wf_module.duplicate(new_tab)
