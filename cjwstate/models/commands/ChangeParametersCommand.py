import logging
from django.contrib.postgres.fields import JSONField
from django.db import models
from cjwstate.models.module_registry import MODULE_REGISTRY
from cjwstate.params import invoke_migrate_params
from ..delta import Delta
from ..step import Step
from .util import ChangesStepOutputs


logger = logging.getLogger(__name__)


class ChangeParametersCommand(ChangesStepOutputs, Delta):
    class Meta:
        app_label = "server"
        db_table = "server_changeparameterscommand"

    step = models.ForeignKey(Step, on_delete=models.PROTECT)
    old_values = JSONField("old_values")  # _all_ params
    new_values = JSONField("new_values")  # only _changed_ params
    step_delta_ids = ChangesStepOutputs.step_delta_ids

    def forward(self):
        self.step.params = self.new_values
        self.step.cached_migrated_params = None
        self.step.cached_migrated_params_module_version = None
        self.step.save(
            update_fields=[
                "params",
                "cached_migrated_params",
                "cached_migrated_params_module_version",
            ]
        )
        self.forward_affected_delta_ids()

    def backward(self):
        self.step.params = self.old_values
        self.step.cached_migrated_params = None
        self.step.cached_migrated_params_module_version = None
        self.step.save(
            update_fields=[
                "params",
                "cached_migrated_params",
                "cached_migrated_params_module_version",
            ]
        )
        self.backward_affected_delta_ids()

    @classmethod
    def step_is_deleted(self, step):
        """Return True iff we cannot add commands to `step`."""
        try:
            step.refresh_from_db()
        except Step.DoesNotExist:
            return True

        if step.is_deleted:
            return True

        step.tab.refresh_from_db()
        if step.tab.is_deleted:
            return True

        return False

    @classmethod
    def amend_create_kwargs(cls, *, step, new_values, **kwargs):
        """
        Prepare `old_values` and `new_values`.

        Raise ValueError if `new_values` won't be valid according to the module
        spec.
        """
        if cls.step_is_deleted(step):  # refreshes from DB
            return None

        try:
            module_zipfile = MODULE_REGISTRY.latest(step.module_id_name)
        except KeyError:
            raise ValueError("Module %s does not exist" % step.module_id_name)

        # Old values: store exactly what we had
        old_values = step.params

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
            "step": step,
            "new_values": new_values,
            "old_values": old_values,
            "step_delta_ids": cls.affected_step_delta_ids(step),
        }

    @property
    def command_description(self):
        return "Change params"
