from django.db import models
from server.models import Delta, WfModule


class ChangeWfModuleUpdateSettingsCommand(Delta):
    wf_module = models.ForeignKey(WfModule, on_delete=models.PROTECT)
    new_auto = models.BooleanField()
    old_auto = models.BooleanField()
    new_next_update = models.DateField(null=True)
    old_next_update = models.DateField(null=True)
    new_update_interval = models.IntegerField()
    old_update_interval = models.IntegerField()

    def forward_impl(self):
        fields = {
            'auto_update_data': self.new_auto,
            'next_update': self.new_next_update,
            'update_interval': self.new_update_interval
        }

        for field, value in fields.items():
            setattr(self.wf_module, field, value)
        self.wf_module.save(update_fields=fields.keys())

    def backward_impl(self):
        fields = {
            'auto_update_data': self.old_auto,
            'next_update': self.old_next_update,
            'update_interval': self.old_update_interval
        }

        for field, value in fields.items():
            setattr(self.wf_module, field, value)
        self.wf_module.save(update_fields=fields.keys())

    @classmethod
    async def create(cls, wf_module, auto_update_data,
                     next_update, update_interval):
        return await cls.create_impl(
            workflow=wf_module.workflow,
            wf_module=wf_module,
            old_auto=wf_module.auto_update_data,
            new_auto=auto_update_data,
            old_next_update=wf_module.next_update,
            new_next_update=next_update,
            old_update_interval=wf_module.update_interval,
            new_update_interval=update_interval
        )

    @property
    def command_description(self):
        return f'Change Workflow update settings'
