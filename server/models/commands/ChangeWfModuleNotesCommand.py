from django.db import models
from server.models import Delta, WfModule


class ChangeWfModuleNotesCommand(Delta):
    wf_module = models.ForeignKey(WfModule, null=True, default=None,
                                  blank=True, on_delete=models.SET_DEFAULT)
    new_value = models.TextField('new_value')
    old_value = models.TextField('old_value')

    def forward_impl(self):
        self.wf_module.notes = self.new_value
        self.wf_module.save()

    def backward_impl(self):
        self.wf_module.notes = self.old_value
        self.wf_module.save()

    @classmethod
    async def create(cls, wf_module, notes):
        old_value = wf_module.notes if wf_module.notes else ''

        return await cls.create_impl(
            workflow=wf_module.workflow,
            wf_module=wf_module,
            new_value=notes,
            old_value=old_value
        )

    @property
    def command_description(self):
        return f'Change WfModule note to {self.new_value}'
