from django.db import models
from .. import Delta, ParameterVal
from .util import ChangesWfModuleOutputs


class ChangeParameterCommand(Delta, ChangesWfModuleOutputs):
    parameter_val = models.ForeignKey(ParameterVal, null=True, default=None,
                                      blank=True, on_delete=models.SET_DEFAULT)
    new_value = models.TextField('new_value')
    old_value = models.TextField('old_value')
    dependent_wf_module_last_delta_ids = \
        ChangesWfModuleOutputs.dependent_wf_module_last_delta_ids

    # Implement wf_module for self.ws_notify()
    @property
    def wf_module(self):
        return self.parameter_val.wf_module

    @property
    def wf_module_id(self):
        return self.parameter_val.wf_module_id

    def forward_impl(self):
        self.parameter_val.value = self.new_value
        self.parameter_val.save(update_fields=['value'])

        self.forward_dependent_wf_module_versions(self.wf_module)
        self.wf_module.save()

    def backward_impl(self):
        self.parameter_val.value = self.old_value
        self.parameter_val.save(update_fields=['value'])

        self.backward_dependent_wf_module_versions(self.wf_module)
        self.wf_module.save()

    @classmethod
    async def create(cls, parameter_val, value):
        workflow = parameter_val.wf_module.workflow

        return await cls.create_impl(
            parameter_val=parameter_val,
            new_value=value or '',
            old_value=parameter_val.value,
            workflow=workflow
        )

    @property
    def command_description(self):
        return f'Change param {self.parameter_val} to {self.new_value}'
