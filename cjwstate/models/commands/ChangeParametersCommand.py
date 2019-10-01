import logging
from django.contrib.postgres.fields import JSONField
from django.db import models
from .. import Delta, WfModule
from cjwstate.modules import loaded_module
from .util import ChangesWfModuleOutputs


logger = logging.getLogger(__name__)


class ChangeParametersCommand(ChangesWfModuleOutputs, Delta):
    class Meta:
        app_label = "server"
        db_table = "server_changeparameterscommand"

    wf_module = models.ForeignKey(WfModule, on_delete=models.PROTECT)
    old_values = JSONField("old_values")  # _all_ params
    new_values = JSONField("new_values")  # only _changed_ params
    wf_module_delta_ids = ChangesWfModuleOutputs.wf_module_delta_ids

    def forward_impl(self):
        self.wf_module.params = self.new_values
        self.wf_module.cached_migrated_params = None
        self.wf_module.cached_migrated_params_module_version = None
        self.wf_module.save(
            update_fields=[
                "params",
                "cached_migrated_params",
                "cached_migrated_params_module_version",
            ]
        )
        self.forward_affected_delta_ids()

    def backward_impl(self):
        self.wf_module.params = self.old_values
        self.wf_module.cached_migrated_params = None
        self.wf_module.cached_migrated_params_module_version = None
        self.wf_module.save(
            update_fields=[
                "params",
                "cached_migrated_params",
                "cached_migrated_params_module_version",
            ]
        )
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
        """
        Prepare `old_values` and `new_values`.

        Raise ValueError if `new_values` won't be valid according to the module
        spec.
        """
        if cls.wf_module_is_deleted(wf_module):  # refreshes from DB
            return None

        module_version = wf_module.module_version
        if module_version is None:
            raise ValueError("Module %s does not exist" % wf_module.module_id_name)

        # Old values: store exactly what we had
        old_values = wf_module.params

        # New values: store _migrated_ old_values, with new_values applied on
        # top
        lm = loaded_module.LoadedModule.for_module_version_sync(module_version)
        migrated_old_values = lm.migrate_params(old_values)
        new_values = {**migrated_old_values, **new_values}

        module_version.param_schema.validate(new_values)  # raises ValueError

        return {
            **kwargs,
            "wf_module": wf_module,
            "new_values": new_values,
            "old_values": old_values,
            "wf_module_delta_ids": cls.affected_wf_module_delta_ids(wf_module),
        }

    @property
    def command_description(self):
        return "Change params"
