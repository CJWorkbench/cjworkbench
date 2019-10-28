import contextlib
from inspect import signature
import io
import math
import sys
import traceback
from typing import Any, ContextManager, Dict, Tuple
import numpy as np
import pandas as pd
from cjwkernel.pandas.validate import validate_dataframe


@contextlib.contextmanager
def _patch_log(name: str, stringio: io.StringIO) -> ContextManager[None]:
    original = getattr(sys, name)
    setattr(sys, name, stringio)
    try:
        yield
    finally:
        setattr(sys, name, original)


def eval_process(code, table):
    """
    Runs `code`'s "process" method; returns (retval, log).

    stdout, stderr, exception tracebacks, and error messages will all be
    written to log. (The UX is: log is displayed as a monospaced console to the
    user -- presumably the person who wrote the code.)

    If there's an Exception `err`, `str(err)` will be returned as the retval.

    This method relies on `cjwkernel.kernel` for sandboxing. The process()
    function can access to anything the module can access.

    This should never raise an exception. (TODO handle out-of-memory.)
    Exceptions would email _us_; but in this case, we want the _user_ to see
    all error messages.
    """
    log = io.StringIO()
    eval_globals = {"pd": pd, "np": np, "math": math}

    def ret(retval):
        """
        Usage: `return ret(whatever)`
        """
        if isinstance(retval, str):
            log.write(retval)
        return (retval, log.getvalue())

    try:
        compiled_code = compile(code, "your code", "exec")
    except SyntaxError as err:
        return ret("Line %d: %s" % (err.lineno, err))
    except ValueError:
        # Apparently this is another thing that compile() can raise
        return ret("Your code contains null bytes")

    # Override sys.stdout and sys.stderr ... but only in the context of
    # `process()`. After `process()`, the module needs its original values
    # again so it can send a Thrift object over stdout and log errors (which
    # should never happen) to stderr.
    #
    # This function's sandbox isn't perfect, but we aren't protecting anything
    # dangerous. Writing to the _original_ `sys.stdout` and `sys.stderr` can at
    # worst cause a single `ModuleExitedError`, which would email us. That's
    # the security risk: an email to us.
    with _patch_log("stdout", log):
        with _patch_log("stderr", log):
            try:
                exec(compiled_code, eval_globals)  # raise any exception

                if "process" not in eval_globals:
                    return ret('Please define a "process(table)" function')
                process = eval_globals["process"]
                if len(signature(process).parameters) != 1:
                    return ret(
                        "Please make your process(table) function accept exactly 1 argument"
                    )

                retval = process(table)
            except Exception:
                # An error in the code or in process()
                etype, value, tb = sys.exc_info()
                tb = tb.tb_next  # omit this method from the stack trace
                traceback.print_exception(etype, value, tb)
                return ret(error=(f"Line {tb.tb_lineno}: {etype.__name__}: {value}"))

    if isinstance(retval, pd.DataFrame):
        try:
            validate_dataframe(retval)  # raise ValueError
        except ValueError as err:
            return ret(
                "Unhandled DataFrame: %s. Please return a different DataFrame."
                % str(err)
            )
        return ret(retval)
    elif isinstance(retval, str):
        return ret(retval)
    else:
        return ret(
            "Please make process(table) return a pd.DataFrame. "
            "(Yours returned a %s.)" % type(retval).__name__
        )


def render(
    table: pd.DataFrame, params: Dict[str, Any]
) -> Tuple[pd.DataFrame, str, Dict[str, str]]:
    code: str = params["code"]

    if not code.strip():
        # empty code, NOP
        return table

    dataframe = pd.DataFrame()
    error = ""
    retval, log = eval_process(code, table)
    if isinstance(retval, pd.DataFrame):
        dataframe = retval
    elif isinstance(retval, str):
        error = retval
    else:
        error = "process() must return a pd.DataFrame or str"

    return (dataframe, error, {"output": log})


def _migrate_params_v0_to_v1(params):
    """
    v0 had an empty-string "run" param, which was the button.

    In v1, the button does not store data.
    """
    return {"code": params["code"]}


def migrate_params(params):
    if "run" in params:
        params = _migrate_params_v0_to_v1(params)
    return params
