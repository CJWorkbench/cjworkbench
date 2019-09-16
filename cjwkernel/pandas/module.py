# This is the "default" module. User code gets executed within the context of
# this file. Then the kernel calls `render_thrift()`, `fetch_thrift()`,
# `migrate_params_thrift()` and `validate()`.

import asyncio
import inspect
import pathlib
import fastparquet
import pandas as pd
import pyarrow
import pyarrow.parquet
from typing import Any, Dict, List, Optional
from cjwkernel import types
from cjwkernel.pandas import types as ptypes
from cjwkernel.thrift import ttypes


def render(table: pd.DataFrame, params: Dict[str, Any], **kwargs):
    """
    Function users should replace in most module code.

    (After building a working `render()`, module authors might consider
    optimizing by rewriting as `render_arrow()` ... and maybe even
    `render_thrift()`.)
    """
    if "fetch_result" in kwargs:
        return kwargs["fetch_result"]
    else:
        return None


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
    input_columns = {
        c.name: ptypes.RenderColumn(
            c.name, c.type.name, getattr(c.type, "format", None)
        )
        for c in input_table_shape.columns
    }
    spec = inspect.getfullargspec(render)
    kwargs = {}
    varkw = bool(spec.varkw)  # if True, function accepts **kwargs
    kwonlyargs = spec.kwonlyargs
    if varkw or "fetch_result" in kwonlyargs:
        kwargs["fetch_result"] = fetch_result
    if varkw or "tab_name" in kwonlyargs:
        kwargs["tab_name"] = tab_name
    if varkw or "input_columns" in kwonlyargs:
        kwargs["input_columns"] = input_columns
    raw_result = render(input_table, params, **kwargs)
    result = ptypes.ProcessResult.coerce(
        raw_result, try_fallback_columns=input_table_shape.columns
    )  # raise ValueError if invalid
    result.truncate_in_place_if_too_big()
    return result


def __arrow_to_pandas(table: types.ArrowTable) -> pd.DataFrame:
    if not table.metadata.columns:
        return pd.DataFrame(index=pd.RangeIndex(0, table.metadata.n_rows))
    else:
        return table.table.to_pandas(
            date_as_object=False, deduplicate_objects=True, ignore_metadata=True
        )  # TODO ensure dictionaries stay dictionaries


def __arrow_column_to_render_column(column: types.Column) -> ptypes.RenderColumn:
    return ptypes.RenderColumn(
        column.name, column.type.name, getattr(column.type, "format", None)
    )


def __arrow_tab_output_to_pandas(tab_output: types.TabOutput) -> ptypes.TabOutput:
    columns = {
        c.name: __arrow_column_to_render_column(c)
        for c in tab_output.table.metadata.columns
    }
    return ptypes.TabOutput(
        tab_output.tab.slug,
        tab_output.tab.name,
        columns,
        __arrow_to_pandas(tab_output.table),
    )


def __parquet_to_pandas(path: pathlib.Path) -> pd.DataFrame:
    if path.stat().st_size == 0:
        return pd.DataFrame()
    else:
        arrow_table = pyarrow.parquet.read_table(str(path), use_threads=False)
        return arrow_table.to_pandas(
            date_as_object=False, deduplicate_objects=True, ignore_metadata=True
        )  # TODO ensure dictionaries stay dictionaries


def _find_tab_outputs(value: Dict[str, Any]) -> List[types.TabOutput]:
    """
    Find all `TabOutput` objects in the param dict, `values`.
    """
    agg: Dict[str, types.TabOutput] = {}  # slug => TabOutput

    def _find_nested(child: Any) -> None:
        if isinstance(child, types.TabOutput):
            nonlocal agg
            agg[child.tab.slug] = child
        elif isinstance(child, dict):
            for grandchild in child.values():
                _find_nested(grandchild)
        elif isinstance(child, list):
            for grandchild in child:
                _find_nested(grandchild)

    _find_nested(value)

    return list(agg.values())


def render_arrow(
    table: types.ArrowTable,
    params: Dict[str, Any],
    tab_name: str,
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
    pandas_table = __arrow_to_pandas(table)
    pandas_input_tabs = {
        to.tab.slug: __arrow_tab_output_to_pandas(to)
        for to in _find_tab_outputs(params)
    }
    if fetch_result is not None:
        fetched_table = __parquet_to_pandas(fetch_result.path)
        if fetch_result.errors:
            assert fetch_result.errors[0].message.id == "TODO_i18n"
            error = fetch_result.errors[0].message.args["text"]
        else:
            error = ""
        pandas_fetch_result = ptypes.ProcessResult(fetched_table, error)
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
    params = types.Params.from_thrift(request.params)
    params_dict = params.params
    if request.fetch_result is None:
        fetch_result = None
    else:
        fetch_result = types.FetchResult.from_thrift(request.fetch_result)

    arrow_result: types.RenderResult = render_arrow(
        arrow_table,
        params_dict,
        request.tab.name,
        fetch_result,
        pathlib.Path(request.output_filename),
    )

    return arrow_result.to_thrift()


def fetch(params: Dict[str, Any], **kwargs):
    """
    Function users should replace in most module code.

    (After building a working `fetch()`, module authors might consider
    optimizing by rewriting as `fetch_arrow()` ... and maybe even
    `fetch_thrift()`.)
    """
    raise NotImplementedError("This module does not define a fetch() function")


def fetch_pandas(
    params: Dict[str, Any],
    secrets: Dict[str, Any],
    last_fetch_result: Optional[types.FetchResult],
    input_table_parquet_path: Optional[pathlib.Path],
) -> ptypes.ProcessResult:
    """
    Call `fetch()` and validate the result.

    Module authors should not replace this function: they should replace
    `fetch()` instead.

    This function validates the `fetch()` return value, to raise a helpful
    `ValueError` if the module code is buggy.
    """
    spec = inspect.getfullargspec(fetch)
    kwargs = {}
    varkw = bool(spec.varkw)  # if True, function accepts **kwargs
    kwonlyargs = spec.kwonlyargs

    if varkw or "secrets" in kwonlyargs:
        kwargs["secrets"] = secrets

    if varkw or "get_input_dataframe" in kwonlyargs:

        async def get_input_dataframe():
            if input_table_parquet_path is None:
                return None
            else:
                return __parquet_to_pandas(input_table_parquet_path)

        kwargs["get_input_dataframe"] = get_input_dataframe

    if varkw or "get_stored_dataframe" in kwonlyargs:

        async def get_stored_dataframe():
            if last_fetch_result is None:
                return None
            else:
                return __parquet_to_pandas(last_fetch_result.path)

        kwargs["get_stored_dataframe"] = get_stored_dataframe

    result = fetch(params, **kwargs)
    if asyncio.iscoroutine(result):
        result = asyncio.run(result)
    return ptypes.ProcessResult.coerce(result)


def fetch_arrow(
    params: Dict[str, Any],
    secrets: Dict[str, Any],
    last_fetch_result: Optional[types.FetchResult],
    input_table_parquet_path: Optional[pathlib.Path],
    output_path: pathlib.Path,
) -> types.FetchResult:
    """
    Render using `cjwkernel.types` data types.

    The result will be encoded as a Parquet file.

    Module authors are encouraged to replace this function, because the
    `fetch()` signature deals in dataframes instead of in raw data.
    """
    pandas_result: ptypes.ProcessResult = fetch_pandas(
        params, secrets, last_fetch_result, input_table_parquet_path
    )
    if len(pandas_result.dataframe.columns):
        fastparquet.write(
            str(output_path),
            pandas_result.dataframe,
            compression="SNAPPY",
            object_encoding="utf8",
        )
    else:
        output_path.write_bytes(b"")
    # Convert from Pandas-style errors to new-style errors. This is a hack
    # because we use a function that converts to Arrow, but we assume it won't
    # actually write to an Arrow file.
    hacky_result = ptypes.ProcessResult(
        dataframe=pd.DataFrame(),
        error=pandas_result.error,
        quick_fixes=pandas_result.quick_fixes,
    )
    errors = hacky_result.to_arrow(None).errors
    return types.FetchResult(output_path, errors)


def fetch_thrift(request: ttypes.FetchRequest) -> ttypes.FetchResult:
    arrow_result = fetch_arrow(
        types.Params.from_thrift(request.params).params,
        types.RawParams.from_thrift(request.secrets).params,
        (
            None
            if request.last_fetch_result is None
            else types.FetchResult.from_thrift(request.last_fetch_result)
        ),
        (
            None
            if request.input_table_parquet_filename is None
            else pathlib.Path(request.input_table_parquet_filename)
        ),
        pathlib.Path(request.output_filename),
    )
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


def migrate_params_thrift(params: ttypes.RawParams):
    params_dict: Dict[str, Any] = types.RawParams.from_thrift(params).params
    result_dict = migrate_params(params_dict)
    return types.RawParams(result_dict).to_thrift()


def validate_thrift() -> ttypes.ValidateModuleResult:
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
        - {"secrets", "get_input_dataframe", "get_stored_dataframe"}
    ), "a fetch() keyword argument is misspelled"

    return ttypes.ValidateModuleResult()
