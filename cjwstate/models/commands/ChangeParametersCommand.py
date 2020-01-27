import logging
from django.contrib.postgres.fields import JSONField
from django.db import models
from .. import Delta, WfModule
from cjwstate.models.module_registry import MODULE_REGISTRY
from cjwstate.params import invoke_migrate_params
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

    def forward(self):
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

    def backward(self):
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

        try:
            module_zipfile = MODULE_REGISTRY.latest(wf_module.module_id_name)
        except KeyError:
            raise ValueError("Module %s does not exist" % wf_module.module_id_name)

        # Old values: store exactly what we had
        old_values = wf_module.params

        module_spec = module_zipfile.get_spec()
        param_schema = module_spec.get_param_schema()

        # New values: store _migrated_ old_values, with new_values applied on
        # top
        migrated_old_values = invoke_migrate_params(module_zipfile, old_values)
        # Ensure migrate_params() didn't generate buggy _old_ values before we
        # add _new_ values. This sanity check may protect users' params by
        # raising an error early. It's also a way to catch bugs in unit tests.
        # (DbTestCaseWithModuleRegistryAndMockKernel default migrate_params
        # returns `{}` -- which is often invalid -- and then the `**new_values`
        # below overwrites the invalid data. So without this validate(), a unit
        # test with an invalid migrate_params() may pass, which is wrong.)
        #
        # If you're seeing this because your unit test failed, try this:
        #     self.kernel.migrate_params.side_effect = lambda m, p: p
        param_schema.validate(migrated_old_values)  # raises ValueError
        new_values = {**migrated_old_values, **new_values}
        param_schema.validate(new_values)  # raises ValueError

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
