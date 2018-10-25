from django.db import models
from server.models import Delta, WfModule
from .util import ChangesWfModuleOutputs


class ChangeDataVersionCommand(Delta, ChangesWfModuleOutputs):
    wf_module = models.ForeignKey(WfModule, null=True, default=None, blank=True, on_delete=models.SET_DEFAULT)
    old_version = models.DateTimeField('old_version', null=True)    # may not have had a previous version
    new_version = models.DateTimeField('new_version')
    dependent_wf_module_last_delta_ids = \
        ChangesWfModuleOutputs.dependent_wf_module_last_delta_ids

    def forward_impl(self):
        self.wf_module.set_fetched_data_version(self.new_version)
        self.forward_dependent_wf_module_versions(self.wf_module)
        self.wf_module.save()

    def backward_impl(self):
        self.backward_dependent_wf_module_versions(self.wf_module)
        self.wf_module.save()
        self.wf_module.set_fetched_data_version(self.old_version)

    @classmethod
    async def create(cls, wf_module, version):
        delta = await cls.create_impl(
            wf_module=wf_module,
            new_version=version,
            old_version=wf_module.get_fetched_data_version(),
            workflow=wf_module.workflow
        )

        return delta

    @property
    def command_description(self):
        return f'Change {self.wf_module.get_module_name()} data version to {self.version}'
