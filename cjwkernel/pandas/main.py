import multiprocessing.reduction
import os
import sys
import types
from typing import Any, List
import thrift.protocol.TBinaryProtocol
import thrift.transport.TTransport
from cjwkernel.types import CompiledModule
import cjwkernel.pandas.module


def main(
    compiled_module: CompiledModule,
    output_fileno: int,
    log_fileno: int,
    function: str,
    *args,
) -> None:
    """
    Run `function` with `args`, and write the (Thrift) result to `output_fileno`.
    """
    # We're writing in text mode so we're forced to buffer output. But we don't
    # want buffering: if we crash, we want whatever was written to be visible
    # to the reader at the other end. So set buffering=1, meaning "line
    # buffering". This is what interactive Python uses for stdout+stderr.
    sys.stdout = os.fdopen(log_fileno, "wt", encoding="utf-8", buffering=1)
    sys.stderr = sys.stdout

    assert function in (
        "render_thrift",
        "migrate_params_thrift",
        "fetch_thrift",
        "validate_thrift",
    )

    run_in_sandbox(output_fileno, compiled_module, function, args)


def run_in_sandbox(
    output_fileno: int, compiled_module: CompiledModule, function: str, args: List[Any]
) -> None:
    """
    Run `function` with `args`, and write the (Thrift) result to `output_fileno`.
    """
    sys.__stdout__ = None
    sys.__stderr__ = None
    # TODO sandbox -- will need an OS `clone()` with namespace, cgroups, ....

    # Run the user's code in a new (programmatic) module.
    #
    # This gives the user code a blank namespace -- exactly what we want.
    module_name = f"rawmodule.{compiled_module.module_slug}"
    user_code_module = types.ModuleType(module_name)
    sys.modules[module_name] = user_code_module  # simulate "import"
    exec(compiled_module.code_object, user_code_module.__dict__)

    # And now ... now we're unsafe! Because `code_object` may be malicious, any
    # line of code from here on out gives undefined behavior. Luckily, a parent
    # is catching all possibile outcomes....

    # Now override the pieces of the _default_ module with the user-supplied
    # ones. That way, when the default `render_pandas()` calls `render()`, that
    # `render()` is the user-code `render()` (if supplied).
    #
    # Good thing we've forked! This totally messes with global variables.
    module = cjwkernel.pandas.module
    for fn in (
        "fetch",
        "fetch_pandas",
        "fetch_thrift",
        "migrate_params",
        "migrate_params_thrift",
        "render",
        "render_arrow",
        "render_pandas",
        "render_thrift",
    ):
        if fn in user_code_module.__dict__:
            module.__dict__[fn] = user_code_module.__dict__[fn]

    if function == "render_thrift":
        result = module.render_thrift(*args)
    elif function == "migrate_params_thrift":
        result = module.migrate_params_thrift(*args)
    elif function == "validate_thrift":
        result = module.validate_thrift(*args)
    elif function == "fetch_thrift":
        result = module.fetch_thrift(*args)
    else:
        raise NotImplementedError

    with os.fdopen(output_fileno, "wb") as f:
        transport = thrift.transport.TTransport.TFileObjectTransport(f)
        protocol = thrift.protocol.TBinaryProtocol.TBinaryProtocol(transport)
        if result is not None:
            result.write(protocol)
