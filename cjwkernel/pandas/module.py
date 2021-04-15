# This is the "default" module. User code gets executed within the context of
# this file. Then the kernel calls `render_thrift()`, `fetch_thrift()`,
# `migrate_params_thrift()` and `validate()`.

import asyncio
import inspect
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import cjwparquet
import cjwpandasmodule
import cjwpandasmodule.convert
import pandas as pd
import pyarrow as pa

from cjwkernel import settings, types
from cjwkernel.pandas import types as ptypes
from cjwkernel.thrift import ttypes
from cjwkernel.types import (
    ArrowTable,
    ColumnType,
    TableMetadata,
    arrow_fetch_result_to_thrift,
    arrow_raw_params_to_thrift,
    arrow_render_result_to_thrift,
    thrift_fetch_result_to_arrow,
    thrift_params_to_arrow,
    thrift_raw_params_to_arrow,
)
from cjwkernel.util import tempfile_context
from cjwkernel.validate import (
    load_trusted_arrow_file,
    load_trusted_arrow_file_with_columns,
)
from cjwmodule.i18n import I18nMessage


def render(table: pd.DataFrame, params: Dict[str, Any], **kwargs):
    """Function users should replace in all module code."""
    if "fetch_result" in kwargs:
        return kwargs["fetch_result"]
    else:
        return None


def __render_pandas(
    *,
    table: types.ArrowTable,
    params: Dict[str, Any],
    tab_name: str,
    fetch_result: Optional[types.FetchResult],
    output_path: Path,
) -> types.RenderResult:
    """Call `render()` with the Pandas signature style.

    Features:

    * Convert input Arrow table to a Pandas dataframe
    * Convert input params to Pandas format (producing extra arguments like
      `input_tabs` as needed).
    * Convert input `fetch_result` to Pandas dataframe, if it is a valid
      Parquet file.
    * Coerce output from a Pandas dataframe to an Arrow table
    * Coerce output errors/json
    """
    # Convert input arguments
    pandas_table = __arrow_to_pandas(table)
    pandas_params = __arrow_param_to_pandas_param(params, output_path.parent)

    spec = inspect.getfullargspec(render)
    kwargs = {}
    varkw = bool(spec.varkw)  # if True, function accepts **kwargs
    kwonlyargs = spec.kwonlyargs
    if varkw or "fetch_result" in kwonlyargs:
        if fetch_result is not None:
            if (
                fetch_result.path.stat().st_size == 0
                or cjwparquet.file_has_parquet_magic_number(fetch_result.path)
            ):
                fetched_table = _parquet_to_pandas(fetch_result.path)
                pandas_fetch_result = ptypes.ProcessResult(
                    fetched_table, fetch_result.errors
                )
            else:
                pandas_fetch_result = fetch_result
        else:
            pandas_fetch_result = None
        kwargs["fetch_result"] = pandas_fetch_result
    if varkw or "settings" in kwonlyargs:
        kwargs["settings"] = settings
    if varkw or "tab_name" in kwonlyargs:
        kwargs["tab_name"] = tab_name
    if varkw or "input_columns" in kwonlyargs:
        kwargs["input_columns"] = {
            c.name: __arrow_column_to_render_column(c) for c in table.metadata.columns
        }
    if varkw or "input_tabs" in kwonlyargs:
        kwargs["input_tabs"] = {
            to.tab.slug: __arrow_tab_output_to_pandas(to, output_path.parent)
            for to in __find_tab_outputs(params)
        }

    # call render()
    raw_result = render(pandas_table, pandas_params, **kwargs)

    # Coerce outputs
    result = ptypes.ProcessResult.coerce(
        raw_result, try_fallback_columns=table.metadata.columns
    )  # raise ValueError if invalid
    result.truncate_in_place_if_too_big()

    return result.to_arrow(output_path)


def __arrow_to_pandas(table: types.ArrowTable) -> pd.DataFrame:
    if not table.metadata.columns:
        return pd.DataFrame(index=pd.RangeIndex(0, table.metadata.n_rows))
    else:
        return cjwpandasmodule.convert.arrow_table_to_pandas_dataframe(table.table)


def _column_type_name(column_type: ColumnType) -> str:
    if isinstance(column_type, ColumnType.Text):
        return "text"
    elif isinstance(column_type, ColumnType.Date):
        return "date"
    elif isinstance(column_type, ColumnType.Number):
        return "number"
    elif isinstance(column_type, ColumnType.Timestamp):
        return "timestamp"
    else:
        raise ValueError("Unhandled column type %r" % column_type)


def __arrow_column_to_render_column(column: types.Column) -> ptypes.RenderColumn:
    return ptypes.RenderColumn(
        column.name,
        _column_type_name(column.type),
        getattr(column.type, "format", getattr(column.type, "unit", None)),
    )


def __arrow_tab_output_to_pandas(
    tab_output: types.TabOutput, basedir: Path
) -> ptypes.TabOutput:
    table, columns = load_trusted_arrow_file_with_columns(
        basedir / tab_output.table_filename
    )
    render_columns = {c.name: __arrow_column_to_render_column(c) for c in columns}
    return ptypes.TabOutput(
        tab_output.tab.slug,
        tab_output.tab.name,
        render_columns,
        cjwpandasmodule.convert.arrow_table_to_pandas_dataframe(table),
    )


def _parquet_to_pandas(path: Path) -> pd.DataFrame:
    if path.stat().st_size == 0:
        return pd.DataFrame()
    else:
        with cjwparquet.open_as_mmapped_arrow(path) as arrow_table:
            return arrow_table.to_pandas(
                date_as_object=False,
                deduplicate_objects=True,
                ignore_metadata=True,
                categories=[
                    column_name.encode("utf-8")
                    for column_name, column in zip(
                        arrow_table.column_names, arrow_table.columns
                    )
                    if hasattr(column.type, "dictionary")
                ],
            )  # TODO ensure dictionaries stay dictionaries


def __find_tab_outputs(value: Dict[str, Any]) -> List[types.TabOutput]:
    """Find all `TabOutput` objects in the param dict, `values`."""
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


def __DEPRECATED_fix_field(
    field: pa.Field, fallback_type: Optional[ColumnType]
) -> pa.Field:
    if pa.types.is_integer(field.type) or pa.types.is_floating(field.type):
        if field.metadata is not None and b"format" in field.metadata:
            return field
        if isinstance(fallback_type, ColumnType.Number):
            return pa.field(
                field.name, field.type, metadata={"format": fallback_type.format}
            )
        return pa.field(field.name, field.type, metadata={"format": "{:,}"})
    if pa.types.is_date32(field.type):
        if field.metadata is not None and b"unit" in field.metadata:
            return field
        if isinstance(fallback_type, ColumnType.Date):
            return pa.field(
                field.name, field.type, metadata={"unit": fallback_type.unit}
            )
        return pa.field(field.name, field.type, metadata={"unit": "day"})
    return field


def __DEPRECATED_overwrite_to_fix_arrow_table_schema(
    path: Path, fallback_column_types: Dict[str, ColumnType]
) -> None:
    if path.stat().st_size > 0:
        table = load_trusted_arrow_file(path)

        untyped_schema = table.schema
        fields = [
            __DEPRECATED_fix_field(
                untyped_schema.field(i), fallback_column_types.get(name)
            )
            for i, name in enumerate(untyped_schema.names)
        ]
        schema = pa.schema(fields)

        # Overwrite with new data
        #
        # We don't short-circuit by comparing schemas: two pa.Schema values
        # with different number formats evaluate as equal.
        #
        # We write a separate file to /var/tmp and then copy it: our sandbox
        # won't let us `rename(2)` in `path`'s directory.
        with tempfile_context(dir="/var/tmp") as rewrite_path:
            with pa.ipc.RecordBatchFileWriter(rewrite_path, schema) as writer:
                writer.write_table(pa.table(table.columns, schema=schema))
            shutil.copyfile(rewrite_path, path)


def __render_arrow(
    *,
    table: types.ArrowTable,
    params: Dict[str, Any],
    tab_name: str,
    fetch_result: Optional[types.FetchResult],
    output_path: Path,
) -> types.RenderResult:
    """Render using `cjwkernel.types` data types.

    Write to `output_path`.

    This will typically call `render()`.
    """
    # call render()
    raw_result = render(
        table.table,
        params,
        output_path,
        columns=table.metadata.columns,
        settings=settings,
        tab_name=tab_name,
        fetch_result=fetch_result,
    )

    # coerce result
    # TODO let module output column types. (Currently, the lack of column types
    # means this is only useful for fetch modules that don't output number
    # formats.)
    __DEPRECATED_overwrite_to_fix_arrow_table_schema(
        output_path,
        fallback_column_types={c.name: c.type for c in table.metadata.columns},
    )
    errors = []
    # TODO support more output types? Or develop the One True Types (maybe
    # types.RenderResult) and force modules to output it.
    if isinstance(raw_result, list):
        # List of I18nMessage errors
        errors = [
            # TODO don't use coerce_I18nMessage? At least, don't use ptypes.
            # Do any modules even require coerce? Or do they all correctly
            # output tuples-or-text? Is it only unit tests that output
            # non-I18nMessage tuples?
            types.RenderError(ptypes.coerce_I18nMessage(message))
            for message in raw_result
        ]
    elif raw_result is None:
        errors = []

    return types.RenderResult(errors=errors)


def __render_by_signature(
    *,
    table: types.ArrowTable,
    params: Dict[str, Any],
    tab_name: str,
    fetch_result: Optional[types.FetchResult],
    output_path: Path,
) -> types.RenderResult:
    """
    Call `__render_arrow()` or `__render_pandas()`, depending on signature.

    Either function calls (user-defined) `render()`, writing to `output_path`.
    """
    spec = inspect.getfullargspec(render)
    if spec.args[0] == "arrow_table":
        fn = __render_arrow
    else:
        fn = __render_pandas

    return fn(
        table=table,
        params=params,
        tab_name=tab_name,
        fetch_result=fetch_result,
        output_path=output_path,
    )


def render_thrift(request: ttypes.RenderRequest) -> ttypes.RenderResult:
    """Render using Thrift data types.

    This function will convert to `cjwkernel.types` (opening Arrow tables in
    the process), call `render_arrow()`, and then convert the result back to
    Thrift. This uses very little RAM.

    Module authors may overwrite this function to avoid reading or writing the
    data table entirely -- for instance, a "change number format" module may
    not need to read any data, so it could operate on the Thrift layer. Most
    modules _do_ look at table data, so they should not overwrite this
    function.
    """
    basedir = Path(request.basedir)
    input_path = basedir / request.input_filename
    table, columns = load_trusted_arrow_file_with_columns(input_path)
    arrow_table = ArrowTable(input_path, table, TableMetadata(table.num_rows, columns))

    params = thrift_params_to_arrow(request.params, basedir)
    params_dict = params.params
    if request.fetch_result is None:
        fetch_result = None
    else:
        fetch_result = thrift_fetch_result_to_arrow(request.fetch_result, basedir)

    arrow_result: types.RenderResult = __render_by_signature(
        table=arrow_table,
        params=params_dict,
        tab_name=request.tab.name,
        fetch_result=fetch_result,
        output_path=basedir / request.output_filename,
    )

    return arrow_render_result_to_thrift(arrow_result)


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


def fetch_pandas(
    params: Dict[str, Any],
    secrets: Dict[str, Any],
    last_fetch_result: Optional[types.FetchResult],
    input_table_parquet_path: Optional[Path],
    output_path: Path,
) -> Union[ptypes.ProcessResult, types.FetchResult]:
    """Call `fetch()` and validate the result.

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
    if varkw or "settings" in kwonlyargs:
        kwargs["settings"] = settings

    if varkw or "get_input_dataframe" in kwonlyargs:

        async def get_input_dataframe():
            if input_table_parquet_path is None:
                return None
            else:
                return _parquet_to_pandas(input_table_parquet_path)

        kwargs["get_input_dataframe"] = get_input_dataframe

    if varkw or "output_path" in kwonlyargs:
        kwargs["output_path"] = output_path

    result = fetch(params, **kwargs)
    if asyncio.iscoroutine(result):
        result = asyncio.run(result)
    if isinstance(result, tuple) and len(result) == 2 and isinstance(result[0], Path):
        errors = ptypes.coerce_RenderError_list(result[1])
        return types.FetchResult(result[0], errors)
    elif isinstance(result, Path):
        return types.FetchResult(result)
    elif isinstance(result, list):
        return types.FetchResult(output_path, ptypes.coerce_RenderError_list(result))
    else:
        return ptypes.ProcessResult.coerce(result)


def __arrow_param_to_pandas_param(param: Any, basedir: Path):
    """
    Recursively prepare `params` to be passed to `render()`.

    * TabOutput gets converted so it has dataframe.
    """
    if isinstance(param, list):
        return [__arrow_param_to_pandas_param(p, basedir) for p in param]
    elif isinstance(param, dict):
        return {k: __arrow_param_to_pandas_param(v, basedir) for k, v in param.items()}
    elif isinstance(param, types.TabOutput):
        return __arrow_tab_output_to_pandas(param, basedir)
    else:
        return param


def fetch_arrow(
    params: Dict[str, Any],
    secrets: Dict[str, Any],
    last_fetch_result: Optional[types.FetchResult],
    input_table_parquet_path: Optional[Path],
    output_path: Path,
) -> types.FetchResult:
    """Render using `cjwkernel.types` data types.

    The result will be encoded as a Parquet file.

    Module authors are encouraged to replace this function, because the
    `fetch()` signature deals in dataframes instead of in raw data.
    """
    pandas_result: Union[ptypes.ProcessResult, types.FetchResult] = fetch_pandas(
        params=__arrow_param_to_pandas_param(params, output_path.parent),
        secrets=secrets,
        last_fetch_result=last_fetch_result,
        input_table_parquet_path=input_table_parquet_path,
        output_path=output_path,
    )
    if isinstance(pandas_result, ptypes.ProcessResult):
        pandas_result.truncate_in_place_if_too_big()
        # ProcessResult => FetchResult isn't a thing; but we can hack it using
        # ProcessResult => RenderResult => FetchResult.
        with tempfile_context(suffix=".arrow") as arrow_path:
            hacky_result = pandas_result.to_arrow(arrow_path)

            if arrow_path.stat().st_size > 0:
                table = load_trusted_arrow_file(arrow_path)
                cjwparquet.write(output_path, table)
            else:
                output_path.write_bytes(b"")
        return types.FetchResult(output_path, hacky_result.errors)
    else:  # it's already a types.FetchResult
        return pandas_result


def fetch_thrift(request: ttypes.FetchRequest) -> ttypes.FetchResult:
    basedir = Path(request.basedir)
    arrow_result = fetch_arrow(
        thrift_params_to_arrow(request.params, basedir).params,
        thrift_raw_params_to_arrow(request.secrets).params,
        (
            None
            if request.last_fetch_result is None
            else thrift_fetch_result_to_arrow(request.last_fetch_result, basedir)
        ),
        (
            None
            if request.input_table_parquet_filename is None
            else basedir / request.input_table_parquet_filename
        ),
        basedir / request.output_filename,
    )
    return arrow_fetch_result_to_thrift(arrow_result)


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


def migrate_params_thrift(params: ttypes.RawParams):
    params_dict: Dict[str, Any] = thrift_raw_params_to_arrow(params).params
    result_dict = migrate_params(params_dict)
    return arrow_raw_params_to_thrift(types.RawParams(result_dict))


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
