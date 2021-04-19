from cjwstate.models.module_registry import MODULE_REGISTRY
from cjwstate.params import invoke_migrate_params
from .base import BaseCommand
from .util import ChangesStepOutputs


def _step_is_deleted(step):
    """Return True iff we cannot add commands to `step`."""
    from ..step import Step

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


class SetStepParams(ChangesStepOutputs, BaseCommand):
    def forward(self, delta):
        delta.step.params = delta.values_for_forward["params"]
        delta.step.cached_migrated_params = None
        delta.step.cached_migrated_params_module_version = None
        delta.step.save(
            update_fields=[
                "params",
                "cached_migrated_params",
                "cached_migrated_params_module_version",
            ]
        )
        self.forward_affected_delta_ids(delta)

    def backward(self, delta):
        delta.step.params = delta.values_for_backward["params"]
        delta.step.cached_migrated_params = None
        delta.step.cached_migrated_params_module_version = None
        delta.step.save(
            update_fields=[
                "params",
                "cached_migrated_params",
                "cached_migrated_params_module_version",
            ]
        )
        self.backward_affected_delta_ids(delta)

    def amend_create_kwargs(self, *, step, new_values, **kwargs):
        """Prepare values_for_backward|forward["params"].

        Raise ValueError if `values_for_forward["params"]` won't be valid
        according to the module spec.
        """
        if _step_is_deleted(step):  # refreshes from DB
            return None

        try:
            module_zipfile = MODULE_REGISTRY.latest(step.module_id_name)
        except KeyError:
            raise ValueError("Module %s does not exist" % step.module_id_name)

        # Old values: store exactly what we had
        old_values = step.params

        module_spec = module_zipfile.get_spec()

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
        module_spec.param_schema.validate(migrated_old_values)  # raises ValueError
        new_values = {**migrated_old_values, **new_values}
        module_spec.param_schema.validate(new_values)  # raises ValueError

        return {
            **kwargs,
            "step": step,
            "values_for_backward": {"params": old_values},
            "values_for_forward": {"params": new_values},
            "step_delta_ids": self.affected_step_delta_ids(step),
        }
