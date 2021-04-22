import asyncio
import inspect
from pathlib import Path
from typing import Any, Callable, Dict

import pandas as pd
import cjwparquet
import cjwpandasmodule
import cjwpandasmodule.convert
from cjwmodule.spec.paramschema import ParamSchema
from cjwmodule.spec.types import ModuleSpec
from cjwmodule.types import RenderError

from cjwkernel import settings, types
from cjwkernel.pandas import types as ptypes
from cjwkernel.pandas.types import arrow_schema_to_render_columns
from cjwkernel.thrift import ttypes
from cjwkernel.types import (
    arrow_render_error_to_thrift,
    arrow_render_result_to_thrift,
    thrift_i18n_message_to_arrow,
    thrift_json_object_to_pydict,
)
from cjwkernel.util import tempfile_context
from cjwkernel.validate import load_trusted_arrow_file, read_columns


def _thrift_tab_output_to_pandas(
    tab_output: ttypes.TabOutput, basedir: Path
) -> ptypes.TabOutput:
    table = load_trusted_arrow_file(basedir / tab_output.table_filename)
    render_columns = arrow_schema_to_render_columns(table.schema)
    return ptypes.TabOutput(
        tab_output.tab_name,
        render_columns,
        cjwpandasmodule.convert.arrow_table_to_pandas_dataframe(table),
    )


def _prepare_params(
    module_spec: ModuleSpec,
    params: Dict[str, Any],
    basedir: Path,
    tab_outputs: Dict[str, ptypes.TabOutput],
) -> Dict[str, Any]:
    """Convert JSON-ish params into params that Pandas-v0 render() expects.

    This walks `module_spec.param_schema`.

    The returned value is the same as `params`, except:

    * File params raise NotImplementedError
    * Tab and Multitab are converted to `ptypes.TabOutput` objects
    """

    def recurse(schema: ParamSchema, value: Any) -> Any:
        if isinstance(schema, ParamSchema.List):
            return [recurse(schema.inner_schema, v) for v in value]
        elif isinstance(schema, ParamSchema.Map):
            return {k: recurse(schema.value_schema, v) for k, v in value.items()}
        elif isinstance(schema, ParamSchema.Dict):
            return {
                name: recurse(inner_schema, value[name])
                for name, inner_schema in schema.properties.items()
            }
        elif isinstance(schema, ParamSchema.Tab):
            return tab_outputs.get(value)  # value=="" => None
        elif isinstance(schema, ParamSchema.Multitab):
            return [tab_outputs[v] for v in value]
        elif isinstance(schema, ParamSchema.File):
            raise NotImplementedError
        else:
            return value

    return recurse(module_spec.param_schema, params)


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


def call_render(
    module_spec: ModuleSpec, render: Callable, request: ttypes.RenderRequest
) -> ttypes.RenderResult:
    basedir = Path(request.basedir)
    input_path = basedir / request.input_filename
    table = load_trusted_arrow_file(input_path)
    dataframe = cjwpandasmodule.convert.arrow_table_to_pandas_dataframe(table)
    tab_outputs = {
        k: _thrift_tab_output_to_pandas(v, basedir)
        for k, v in request.tab_outputs.items()
    }
    params = _prepare_params(
        module_spec, thrift_json_object_to_pydict(request.params), basedir, tab_outputs
    )
    spec = inspect.getfullargspec(render)
    kwargs = {}
    varkw = bool(spec.varkw)  # if True, function accepts **kwargs
    kwonlyargs = spec.kwonlyargs
    if varkw or "fetch_result" in kwonlyargs:
        if request.fetch_result is None:
            fetch_result = None
        else:
            fetch_result_path = basedir / request.fetch_result.filename
            errors = [
                # Data comes in as FetchError and we return RenderError.
                RenderError(thrift_i18n_message_to_arrow(e.message))
                for e in request.fetch_result.errors
            ]
            if (
                fetch_result_path.stat().st_size == 0
                or cjwparquet.file_has_parquet_magic_number(fetch_result_path)
            ):
                fetch_result = ptypes.ProcessResult(
                    dataframe=_parquet_to_pandas(fetch_result_path),
                    errors=errors,
                    # infer columns -- the fetch interface doesn't handle formats
                    # (TODO nix pandas_v0 fetching altogether by rewriting all modules)
                )
            else:
                # TODO nix pandas Fetch modules. (Do any use files, even?)
                fetch_result = types.FetchResult(path=fetch_result_path, errors=errors)
        kwargs["fetch_result"] = fetch_result
    if varkw or "settings" in kwonlyargs:
        kwargs["settings"] = settings
    if varkw or "tab_name" in kwonlyargs:
        kwargs["tab_name"] = request.tab_name
    if varkw or "input_columns" in kwonlyargs:
        kwargs["input_columns"] = arrow_schema_to_render_columns(table.schema)

    input_columns = read_columns(table, full=False)
    raw_result = render(dataframe, params, **kwargs)

    # raise ValueError if invalid
    pandas_result = ptypes.ProcessResult.coerce(
        raw_result, try_fallback_columns=input_columns
    )
    pandas_result.truncate_in_place_if_too_big()

    arrow_result = pandas_result.to_arrow(basedir / request.output_filename)
    return arrow_render_result_to_thrift(arrow_result)


def call_fetch(fetch: Callable, request: ttypes.FetchRequest) -> ttypes.FetchResult:
    """Call `fetch()` and validate the result.

    Module code may contain errors. This function and `fetch()` should strive
    to raise developer-friendly errors in the case of bugs -- including
    unexpected input.
    """
    # thrift => pandas
    basedir = Path(request.basedir)
    params: Dict[str, Any] = thrift_json_object_to_pydict(request.params)
    output_path = basedir / request.output_filename

    spec = inspect.getfullargspec(fetch)
    kwargs = {}
    varkw = bool(spec.varkw)  # if True, function accepts **kwargs
    kwonlyargs = spec.kwonlyargs

    if varkw or "secrets" in kwonlyargs:
        kwargs["secrets"] = thrift_json_object_to_pydict(request.secrets)
    if varkw or "settings" in kwonlyargs:
        kwargs["settings"] = settings
    if varkw or "get_input_dataframe" in kwonlyargs:

        async def get_input_dataframe():
            if request.input_table_parquet_filename is None:
                return None
            else:
                return _parquet_to_pandas(
                    basedir / request.input_table_parquet_filename
                )

        kwargs["get_input_dataframe"] = get_input_dataframe

    if varkw or "output_path" in kwonlyargs:
        kwargs["output_path"] = output_path

    result = fetch(params, **kwargs)
    if asyncio.iscoroutine(result):
        result = asyncio.run(result)

    if isinstance(result, tuple) and len(result) == 2 and isinstance(result[0], Path):
        errors = ptypes.coerce_RenderError_list(result[1])
    elif isinstance(result, Path):
        errors = []
    elif isinstance(result, list):
        errors = ptypes.coerce_RenderError_list(result)
    else:
        pandas_result = ptypes.ProcessResult.coerce(result)
        pandas_result.truncate_in_place_if_too_big()
        # ProcessResult => FetchResult isn't a thing; but we can hack it using
        # ProcessResult => RenderResult => FetchResult.
        with tempfile_context(suffix=".arrow") as arrow_path:
            if pandas_result.columns:
                hacky_result = pandas_result.to_arrow(arrow_path)
                table = load_trusted_arrow_file(arrow_path)
                cjwparquet.write(output_path, table)
                errors = hacky_result.errors
            else:
                output_path.write_bytes(b"")
                errors = pandas_result.errors

    return ttypes.FetchResult(
        filename=request.output_filename,
        errors=[arrow_render_error_to_thrift(e) for e in errors],
    )
