from django.contrib.postgres.fields import JSONField
from django.db import models
from .. import Delta, WfModule
from .util import ChangesWfModuleOutputs


class ChangeParametersCommand(Delta, ChangesWfModuleOutputs):
    wf_module = models.ForeignKey(WfModule, on_delete=models.PROTECT)
    old_values = JSONField('old_values')  # _all_ params
    new_values = JSONField('new_values')  # only _changed_ params
    wf_module_delta_ids = ChangesWfModuleOutputs.wf_module_delta_ids

    def forward_impl(self):
        self.wf_module.params = {
            **self.old_values,
            **self.new_values
        }
        self.wf_module.save(update_fields=['params'])
        self.forward_affected_delta_ids()

    def backward_impl(self):
        self.wf_module.params = self.old_values
        self.wf_module.save(update_fields=['params'])
        self.backward_affected_delta_ids()

    @classmethod
    def wf_module_is_deleted(self, wf_module):
        """Return True iff we cannot add commands to `wf_module`."""
        try:
            wf_module.refresh_from_db()
        except WfModule.DoesNotExist:
            return True

        if wf_module.is_deleted:
            return True

        wf_module.tab.refresh_from_db()
        if wf_module.tab.is_deleted:
            return True

        return False

    @classmethod
    def amend_create_kwargs(cls, *, wf_module, new_values, **kwargs):
        if cls.wf_module_is_deleted(wf_module):  # refreshes from DB
            return None

        old_values = wf_module.params

        if old_values is None:
            # TODO nix this when we set WfModule.params to NOT NULL
            params = wf_module.get_params()
            old_values = params.as_dict()
            # Delete secrets
            for key in params.secrets.keys():
                del old_values[key]

        # TODO migrate params here: when the user changes params, we want to
        # save something consistent.

        return {
            **kwargs,
            'wf_module': wf_module,
            'new_values': new_values,
            'old_values': old_values,
            'wf_module_delta_ids': cls.affected_wf_module_delta_ids(wf_module),
        }

    @property
    def command_description(self):
        return f"Change params {', '.join(self.old_values.keys())}"
