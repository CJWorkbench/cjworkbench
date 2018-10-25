from django.contrib.postgres.fields import JSONField
from django.db import models
from .. import Delta, WfModule
from .util import ChangesWfModuleOutputs


class ChangeParametersCommand(Delta, ChangesWfModuleOutputs):
    wf_module = models.ForeignKey(WfModule, null=False)
    old_values = JSONField('old_values')
    new_values = JSONField('new_values')

    dependent_wf_module_last_delta_ids = \
        ChangesWfModuleOutputs.dependent_wf_module_last_delta_ids

    def _apply_values(self, values):
        pvs = list(self.wf_module.parameter_vals
                   .prefetch_related('parameter_spec').all())
        for pv in pvs:
            id_name = pv.parameter_spec.id_name
            if id_name in values:
                pv.value = values[id_name]
                pv.save(update_fields=['value'])

    def forward_impl(self):
        self._apply_values(self.new_values)
        self.forward_dependent_wf_module_versions(self.wf_module)
        self.wf_module.save()

    def backward_impl(self):
        self._apply_values(self.old_values)
        self.backward_dependent_wf_module_versions(self.wf_module)
        self.wf_module.save()

    @classmethod
    def amend_create_kwargs(cls, *, wf_module, new_values, **kwargs):
        old_values = dict(
            wf_module.parameter_vals
            .filter(parameter_spec__id_name__in=new_values.keys())
            .values_list('parameter_spec__id_name', 'value')
        )

        return {
            **kwargs,
            'wf_module': wf_module,
            'new_values': new_values,
            'old_values': old_values,
        }

    @property
    def command_description(self):
        return f"Change params {', '.join(self.old_values.keys())}"
