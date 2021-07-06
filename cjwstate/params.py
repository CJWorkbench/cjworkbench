import logging
import time
from typing import Any, Dict

import cjwstate.modules
from cjwkernel.errors import ModuleError
from cjwstate.models import Step
from cjwstate.models.module_registry import MODULE_REGISTRY
from cjwstate.modules.types import ModuleZipfile


logger = logging.getLogger(__name__)


def get_migrated_params(
    step: Step, *, module_zipfile: ModuleZipfile = None
) -> Dict[str, Any]:
    """Read `step.params`, calling migrate_params() or using cache fields.

    Call this within a `Workflow.cooperative_lock()`.

    If migrate_params() was already called for this version of the module,
    return the cached value. See `step.cached_migrated_params`,
    `step.cached_migrated_params_module_version`.

    Raise `ModuleError` if migration fails.

    Raise `KeyError` if the module was deleted.

    Raise `RuntimeError` (unrecoverable) if there is a problem loading or
    executing the module. (Modules are validated before import, so this should
    not happen.)

    The result may be invalid. Call `validate()` to raise a `ValueError` to
    detect that case.

    TODO avoid holding the database lock whilst executing stuff on the kernel.
    (This will involve auditing and modifying all callers to handle new error
    cases.)
    """
    if module_zipfile is None:
        # raise KeyError
        module_zipfile = MODULE_REGISTRY.latest(step.module_id_name)

    stale = (
        module_zipfile.version == "develop"
        # works if cached version (and thus cached _result_) is None
        or module_zipfile.version != step.cached_migrated_params_module_version
    )

    if not stale:
        return step.cached_migrated_params
    else:
        # raise ModuleError
        params = invoke_migrate_params(module_zipfile, step.params)
        step.cached_migrated_params = params
        step.cached_migrated_params_module_version = module_zipfile.version
        try:
            step.save(
                update_fields=[
                    "cached_migrated_params",
                    "cached_migrated_params_module_version",
                ]
            )
        except ValueError:
            # Step was deleted, so we get:
            # "ValueError: Cannot force an update in save() with no primary key."
            pass
        return params


def invoke_migrate_params(
    module_zipfile: ModuleZipfile, raw_params: Dict[str, Any]
) -> Dict[str, Any]:
    """Call module `migrate_params()` using (global) kernel.

    Raise ModuleError if module code did not execute.

    The result may not be valid. Call `param_schema.validate(result)` to
    raise `ValueError` on error; or call `param_schema.coerce(result)` to
    guarantee a valid result.

    Log any ModuleError. Also log success.
    """
    time1 = time.time()
    logger.info("%s:migrate_params() begin", module_zipfile.path.name)
    status = "???"
    try:
        result = cjwstate.modules.kernel.migrate_params(
            module_zipfile.compile_code_without_executing(), raw_params
        )  # raise ModuleError
        status = "ok"
        return result
    except ModuleError as err:
        logger.exception("Exception in %s:migrate_params()", module_zipfile.path.name)
        status = type(err).__name__
        raise
    finally:
        time2 = time.time()
        logger.info(
            "%s:migrate_params() => %s in %dms",
            module_zipfile.path.name,
            status,
            int((time2 - time1) * 1000),
        )
