import io
import math
import sys
import traceback
from contextlib import redirect_stderr, redirect_stdout
from inspect import signature
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd
from cjwpandasmodule.validate import validate_dataframe

EMPTY_DATAFRAME = pd.DataFrame()


def eval_process(code, table):
    """Runs `code`'s "process" method; return (retval, error, log).

    stdout, stderr, exception tracebacks, and error messages will all be
    written to log. (The UX is: log is displayed as a monospaced console to the
    user -- presumably the person who wrote the code.)

    If there's an Exception `err`, `str(err)` will be returned as the retval.

    This function doesn't a sandbox! It isn't secure! It merely captures
    output.

    This should never raise an exception. An exception is a bug in this
    _module_. A bug in _user code_ must be presented to the user. (TODO handle
    timeout, out-of-memory.)
    """
    log = io.StringIO()
    eval_globals = {"pd": pd, "np": np, "math": math}

    def ret(dataframe: pd.DataFrame = EMPTY_DATAFRAME, error: str = ""):
        """Usage: `return ret(table, message)`"""
        log.write(error)
        return dataframe, error, log.getvalue()

    try:
        compiled_code = compile(code, "your code", "exec")
    except SyntaxError as err:
        return ret(error="Line %d: %s" % (err.lineno, err))
    except ValueError:
        # Apparently this is another thing that compile() can raise
        return ret(error="Your code contains null bytes")

    # Override sys.stdout and sys.stderr ... but only in the context of
    # `process()`. After `process()`, the module needs its original values
    # again so it can send a Thrift object over stdout and log errors (which
    # should never happen) to stderr.
    #
    # This function's sandbox isn't perfect, but we aren't protecting anything
    # dangerous. Writing to the _original_ `sys.stdout` and `sys.stderr` can at
    # worst cause a single `ModuleExitedError`, which would email us. That's
    # the security risk: an email to us.
    with redirect_stdout(log), redirect_stderr(log):
        try:
            exec(compiled_code, eval_globals)  # raise any exception

            if "process" not in eval_globals:
                return ret(error='Please define a "process(table)" function')
            process = eval_globals["process"]
            if len(signature(process).parameters) != 1:
                return ret(
                    error="Please make your process(table) function accept exactly 1 argument"
                )

            retval = process(table)  # raise any exception
        except Exception:
            # An error in the code or in process()
            etype, value, tb = sys.exc_info()
            tb = tb.tb_next  # omit this method from the stack trace
            traceback.print_exception(etype, value, tb)
            return ret(error=f"Line {tb.tb_lineno}: {etype.__name__}: {value}")

    if isinstance(retval, pd.DataFrame):
        try:
            validate_dataframe(retval)  # raise ValueError
        except ValueError as err:
            return ret(error="Unhandled DataFrame: %s" % str(err))
        return ret(retval)
    elif isinstance(retval, str):
        return ret(error=retval)
    else:
        return ret(
            error=(
                "Please make process(table) return a pd.DataFrame. "
                "(Yours returned a %s.)" % type(retval).__name__
            )
        )


def render(
    table: pd.DataFrame, params: Dict[str, Any]
) -> Tuple[pd.DataFrame, str, Dict[str, str]]:
    code: str = params["code"]

    if code.strip():
        dataframe, error, log = eval_process(code, table)
    else:
        # empty code, NOP
        dataframe = table
        error = ""
        log = ""

    return dataframe, error, {"output": log}


def _migrate_params_v0_to_v1(params):
    """v0 had an empty-string "run" param, which was the button.

    In v1, the button does not store data.
    """
    return {"code": params["code"]}


def migrate_params(params):
    if "run" in params:
        params = _migrate_params_v0_to_v1(params)
    return params
