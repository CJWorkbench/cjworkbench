from typing import Any, Dict
from cjwstate.models import WfModule
from cjwstate.modules.loaded_module import LoadedModule


def get_migrated_params(wf_module: WfModule) -> Dict[str, Any]:
    """
    Read `wf_module.params`, calling migrate_params() or using cache fields.

    Call this within a `Workflow.cooperative_lock()`.

    If migrate_params() was already called for this version of the module,
    return the cached value. See `wf_module.cached_migrated_params`,
    `wf_module.cached_migrated_params_module_version`.

    Raise `ModuleError` if migration fails.

    Return `{}` if the module was deleted.

    The result may be invalid. Call `validate()` to raise a `ValueError` to
    detect that case.
    """
    module_version = wf_module.module_version
    if module_version is None:
        return {}

    if module_version.source_version_hash == "develop":
        stale = True
    elif (
        # works if cached version (and thus cached _result_) is None
        module_version.param_schema_version
        != wf_module.cached_migrated_params_module_version
    ):
        stale = True
    else:
        stale = False

    if not stale:
        return wf_module.cached_migrated_params
    else:
        loaded_module = LoadedModule.for_module_version(module_version)
        if loaded_module:
            params = wf_module.params  # the user-supplied params
            params = loaded_module.migrate_params(params)  # raises ModuleError
            wf_module.cached_migrated_params = params
            wf_module.cached_migrated_params_module_version = (
                module_version.param_schema_version
            )
            # Write to DB, like wf_module.save(fields=[...]), even if the
            # WfModule was deleted in a race
            WfModule.objects.filter(id=wf_module.id).update(
                cached_migrated_params=wf_module.cached_migrated_params,
                cached_migrated_params_module_version=(
                    wf_module.cached_migrated_params_module_version
                ),
            )
            return params
        else:
            return {}
