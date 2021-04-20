# This is the "default" module. User code gets executed within the context of
# this file. Then the kernel calls `render_thrift()`, `fetch_thrift()`,
# `migrate_params_thrift()` and `validate()`.

import inspect
from typing import Any, Dict

from cjwkernel.thrift import ttypes
from cjwkernel.types import pydict_to_thrift_json_object, thrift_json_object_to_pydict
from .framework import arrow_v0, pandas_v0


def render(table, params: Dict[str, Any], **kwargs):
    """Function users should replace in all module code."""
    if "fetch_result" in kwargs:
        return kwargs["fetch_result"]
    else:
        return None


def render_thrift(request: ttypes.RenderRequest) -> ttypes.RenderResult:
    spec = inspect.getfullargspec(render)
    if spec.args[0] == "arrow_table":
        framework = arrow_v0
    else:
        framework = pandas_v0

    global ModuleSpec  # injected by cjwkernel.pandas.main
    framework.ModuleSpec = ModuleSpec

    return framework.call_render(render, request)


def fetch(params: Dict[str, Any], **kwargs):
    """Function users should replace in most module code.

    (After building a working `fetch()`, module authors might consider
    optimizing by rewriting as `fetch_arrow()` ... and maybe even
    `fetch_thrift()`.)

    Valid return types:

    * pd.DataFrame -> becomes a Parquet file
    * (pd.DataFrame, str) -> Parquet file plus warning
    * str -> error
    * Path -> raw file
    * (Path, str) -> raw file plus warning
    """
    raise NotImplementedError("This module does not define a fetch() function")


def fetch_thrift(request: ttypes.FetchRequest) -> ttypes.FetchResult:
    if "fetch_arrow" in globals():
        framework = arrow_v0
        fetch = globals()["fetch_arrow"]
    else:
        framework = pandas_v0
        fetch = globals()["fetch"]

    return framework.call_fetch(fetch, request)


def migrate_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Function users should replace in most module code.

    The input `params` are any params that were _ever_ returned from
    `migrate_params()` -- back to the beginning of time. Basically, if a the
    module spec allowed a certain arrangement of `params`, it must be accepted
    as input to `migrate_params()`.

    The output is a `params` that must be valid according to the module spec.

    Module authors should "version" their parameter specs using function names
    and comments. They should plan for the future and write append-only code.
    This pattern has proven effective:

        def migrate_params(params):
            if _is_params_v1(params):
                params = _migrate_params_v1_to_v2(params)
            if _is_params_v2(params):
                params = _migrate_params_v2_to_v3(params)
            return params

    Module authors should also unit-test that all params can be passed to
    `migrate_params()` and produce valid (and expected) output params.

    The default operation is a no-op.
    """
    return params


def migrate_params_thrift(thrift_params: Dict[str, ttypes.Json]):
    params_dict: Dict[str, Any] = thrift_json_object_to_pydict(thrift_params)
    result_dict = migrate_params(params_dict)
    return ttypes.MigrateParamsResult(pydict_to_thrift_json_object(result_dict))


def validate_thrift() -> ttypes.ValidateModuleResult:
    """Crash with an error to stdout if something about this module seems amiss.

    This does not prove the module is bug-free. It just helps catch some errors
    early.

    There are three types of error we can catch early in a module:

    * Compile error (such as a syntax error) -- we never get to call validate()
    * Exec error (such as bad global variable ref) -- we never get to call
      validate()
    * Validate error (such as wrong `render()` signature) -- this is what
      validate() can catch.
    """
    render_spec = inspect.getfullargspec(render)
    assert render_spec.varargs is None, "render must not accept varargs"
    if len(render_spec.args) == 3:
        assert render_spec.args[0] == "arrow_table", (
            "render must take two positional arguments, "
            "or its first argument must be `arrow_table`"
        )
        assert render_spec.args[2] == "output_path", (
            "render must take two positional arguments, "
            "or its third argument must be `output_path`"
        )
        assert (
            render_spec.varkw
        ), "render() must accept **kwargs (for forward-compatibility)"
        assert not (
            set(render_spec.kwonlyargs)
            - {"fetch_result", "columns", "settings", "tab_name"}
        ), "a render() keyword argument is misspelled"
    else:
        assert len(render_spec.args) == 2, "render must take two positional arguments"
        assert not (
            set(render_spec.kwonlyargs)
            - {"fetch_result", "tab_name", "input_columns", "settings"}
        ), "a render() keyword argument is misspelled"

    migrate_params_spec = inspect.getfullargspec(migrate_params)
    assert (
        len(migrate_params_spec.args) == 1
    ), "migrate_params must take one positional argument"
    assert migrate_params_spec.varargs is None, "migrate_params must not accept varargs"
    assert migrate_params_spec.varkw is None, "migrate_params must not accept kwargs"
    assert not migrate_params_spec.kwonlyargs, "migrate_params must not accept kwargs"

    fetch_spec = inspect.getfullargspec(fetch)
    assert fetch_spec.varargs is None, "fetch must not accept varargs"
    assert len(fetch_spec.args) == 1, "fetch must take one positional argument"
    assert not (
        set(fetch_spec.kwonlyargs)
        - {
            "secrets",
            "get_input_dataframe",
            "get_stored_dataframe",
            "output_path",
            "settings",
        }
    ), "a fetch() keyword argument is misspelled"

    return ttypes.ValidateModuleResult()
