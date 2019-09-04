import multiprocessing.reduction
import os
import sys
from typing import Any, List
import thrift.protocol.TBinaryProtocol
import thrift.transport.TTransport
from cjwkernel.types import CompiledModule
import cjwkernel.pandas.module


def main(
    compiled_module: CompiledModule,
    output_dup_fd: multiprocessing.reduction.DupFd,
    log_dup_fd: multiprocessing.reduction.DupFd,
    function: str,
    *args,
) -> None:
    """
    Run `function` with `args`, and write the (Thrift) result to `output_fileno`.
    """
    output_fileno = output_dup_fd.detach()
    log_fileno = log_dup_fd.detach()

    sys.stdout = os.fdopen(log_fileno, "wt", encoding="utf-8")
    sys.stderr = sys.stdout

    assert function in ("render", "migrate_params", "fetch", "validate")

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

    # Start with the default module, then exec() to override with user code.
    module = cjwkernel.pandas.module
    exec(compiled_module.code_object, module.__dict__, module.__dict__)
    # And now ... now we're unsafe! Because `code_object` may be malicious, any
    # line of code from here on out gives undefined behavior. Luckily, a parent
    # is catching all possibile outcomes....

    if function == "render":
        result = module.render_thrift(*args)
    if function == "migrate_params":
        result = module.migrate_params_thrift(*args)
    elif function == "validate":
        result = module.validate(*args)
    elif function == "fetch":
        result = module.fetch_thrift(*args)

    with os.fdopen(output_fileno, "wb") as f:
        transport = thrift.transport.TTransport.TFileObjectTransport(f)
        protocol = thrift.protocol.TBinaryProtocol.TBinaryProtocol(transport)
        if result is not None:
            result.write(protocol)
