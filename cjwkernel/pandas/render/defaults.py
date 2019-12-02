# This is the "default" module. User code gets executed within the context of
# this file. Then the kernel calls `render_thrift()`, `fetch_thrift()`,
# `migrate_params_thrift()` and `validate()`.

import inspect
import json
import os
import pathlib
import tempfile
import pandas as pd
import pyarrow
from typing import Any, Dict, Optional
from cjwkernel import types
from cjwkernel.pandas import types as ptypes
from cjwkernel.thrift import ttypes
from cjwkernel.util import json_encode


def render(table: pd.DataFrame, params: Dict[str, Any], **kwargs):
    """
    Function users should replace in most module code.

    (After building a working `render()`, module authors might consider
    optimizing by rewriting as `render_arrow()` ... and maybe even
    `render_thrift()`.)
    """
    raise NotImplementedError("This module does not define a render() function")


def render_pandas(
    input_table: pd.DataFrame,
    input_table_shape: ptypes.TableShape,
    params: Dict[str, Any],
    tab_name: str,
    input_tabs: Dict[str, ptypes.TabOutput],
    fetch_result: Optional[ptypes.ProcessResult],
) -> ptypes.ProcessResult:
    """
    Call `render()` and validate the result.

    Module authors should not replace this function: they should replace
    `render()` instead.

    This function validates the `render()` return value, to raise a helpful
    ValueError if the module code is buggy.
    """
    spec = inspect.getfullargspec(render)
    kwargs = {}
    varkw = bool(spec.varkw)  # if True, function accepts **kwargs
    kwonlyargs = spec.kwonlyargs
    if varkw or "fetch_result" in kwonlyargs:
        kwargs["fetch_result"] = fetch_result
    if varkw or "tab_name" in kwonlyargs:
        kwargs["tab_name"] = tab_name
    if varkw or "input_columns" in kwonlyargs:
        kwargs["input_columns"] = {
            c.name: ptypes.RenderColumn(
                c.name, c.type.name, getattr(c.type, "format", None)
            )
            for c in input_table_shape.columns
        }
    raw_result = render(input_table, params, **kwargs)
    return ptypes.ProcessResult.coerce(raw_result)  # raise ValueError if invalid


def __arrow_to_pandas(table: pyarrow.Table) -> pd.DataFrame:
    return table.to_pandas(
        date_as_object=False, deduplicate_objects=True, ignore_metadata=True
    )  # TODO ensure dictionaries stay dictionaries


def __parquet_to_pandas(path: pathlib.Path) -> pd.DataFrame:
    arrow_table = pyarrow.parquet.read_table(str(path), use_threads=False)
    return __arrow_to_pandas(arrow_table)


def render_arrow(
    table: types.ArrowTable,
    params: Dict[str, Any],
    tab_name: str,
    input_tabs: Dict[str, types.TabOutput],
    fetch_result: Optional[types.FetchResult],
    output_path: pathlib.Path,
) -> types.RenderResult:
    """
    Render using `cjwkernel.types` data types.

    If outputting Arrow data, write to `output_path`.

    Module authors are encouraged to replace this function, because Arrow
    tables are simpler and more memory-efficient than Pandas tables. This is
    the ideal signature for a "rename columns" module, for instance: Arrow
    can pass data through without consuming excessive RAM.

    This does not validate the render_pandas() return value.
    """
    pandas_table = __arrow_to_pandas(table.table)
    pandas_input_tabs = {k: __arrow_to_pandas(v) for k, v in input_tabs.items()}
    if fetch_result is not None:
        fetched_table = __parquet_to_pandas(fetch_result.path)
        pandas_fetch_result = ptypes.ProcessResult.coerce(
            (fetched_table, [error.to_pandas_error() for error in fetch_result.errors])
        )
    else:
        pandas_fetch_result = None

    pandas_result: ptypes.ProcessResult = render_pandas(
        input_table=pandas_table,
        input_table_shape=ptypes.TableShape.from_arrow(table.metadata),
        params=params,
        tab_name=tab_name,
        input_tabs=pandas_input_tabs,
        fetch_result=pandas_fetch_result,
    )

    return pandas_result.to_arrow(output_path)


def render_thrift(request: ttypes.RenderRequest) -> ttypes.RenderResult:
    """
    Render using Thrift data types.

    This function will convert to `cjwkernel.types` (opening Arrow tables in
    the process), call `render_arrow()`, and then convert the result back to
    Thrift. This uses very little RAM.

    Module authors may overwrite this function to avoid reading or writing the
    data table entirely -- for instance, a "change number format" module may
    not need to read any data, so it could operate on the Thrift layer. Most
    modules _do_ look at table data, so they should not overwrite this
    function.
    """
    arrow_table = types.ArrowTable.from_thrift(request.input_table)
    params_dict = json.loads(request.params.json)
    arrow_input_tabs = {
        k: types.TabOutput.from_thrift(v) for k, v in request.input_tabs.items()
    }
    if request.fetch_result is None:
        fetch_result = None
    else:
        fetch_result = types.FetchResult.from_thrift(request.fetch_result)

    fd, filename = tempfile.mkstemp(dir=".")
    os.close(fd)

    try:
        arrow_result: types.RenderResult = render_arrow(
            arrow_table,
            params_dict,
            request.tab.name,
            arrow_input_tabs,
            fetch_result,
            pathlib.Path(filename),
        )
    except Exception:
        os.unlink(filename)
        raise

    if arrow_result.arrow_table.path is None:
        os.unlink(filename)

    return arrow_result.to_thrift()


def migrate_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Function users should replace in most module code.

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


def migrate_params_thrift(params: ttypes.Params):
    params_dict: Dict[str, Any] = json.loads(params.json)
    result_dict = migrate_params(params_dict)
    result_json = json_encode(result_dict)
    return ttypes.Params(result_json)


def validate() -> None:
    """
    Crash with an error to stdout if something about this module seems amiss.

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
    assert len(render_spec.args) == 2, "render must take two positional arguments"
    assert not (
        set(render_spec.kwonlyargs) - {"fetch_result", "tab_name", "input_columns"}
    ), "one of this module's keyword arguments is misspelled"

    migrate_params_spec = inspect.getfullargspec(migrate_params)
    assert (
        len(migrate_params_spec.args) == 1
    ), "migrate_params must take one positional argument"
    assert migrate_params_spec.varargs is None, "migrate_params must not accept varargs"
    assert migrate_params_spec.varkw is None, "migrate_params must not accept kwargs"
    assert not migrate_params_spec.kwonlyargs, "migrate_params must not accept kwargs"

    return ttypes.ValidateModuleResult()
