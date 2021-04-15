import shutil
from pathlib import Path
from typing import Any, Callable, Dict, NamedTuple, Optional

import pyarrow as pa

from cjwkernel import settings
from cjwkernel.pandas.types import coerce_RenderError_list
from cjwkernel.thrift import ttypes
from cjwkernel.types import (
    arrow_fetch_result_to_thrift,
    arrow_render_error_to_thrift,
    thrift_fetch_result_to_arrow,
    thrift_params_to_arrow,
    thrift_raw_params_to_arrow,
)
from cjwkernel.util import tempfile_context
from cjwkernel.validate import (
    load_trusted_arrow_file,
    load_trusted_arrow_file_with_columns,
)


class ArrowTable(NamedTuple):
    """Table on disk, opened and mmapped.

    This is passed to deprecated Arrow-based modules.
    """

    path: Path
    """Name of file on disk that contains data."""

    table: pa.Table
    """Pyarrow table, loaded with mmap."""


def __DEPRECATED_fix_field(
    field: pa.Field, fallback_field: Optional[pa.Field]
) -> pa.Field:
    if pa.types.is_integer(field.type) or pa.types.is_floating(field.type):
        if field.metadata is not None and b"format" in field.metadata:
            return field
        if fallback_field.metadata and b"format" in fallback_field.metadata:
            return pa.field(field.name, field.type, metadata=fallback_field.metadata)
        return pa.field(field.name, field.type, metadata={"format": "{:,}"})
    if pa.types.is_date32(field.type):
        if field.metadata is not None and b"unit" in field.metadata:
            return field
        if fallback_field.metadata and b"unit" in fallback_field.metadata:
            return pa.field(field.name, field.type, metadata=fallback_field.metadata)
        return pa.field(field.name, field.type, metadata={"unit": "day"})
    return field


def _DEPRECATED_overwrite_to_fix_arrow_table_schema(
    path: Path, fallback_schema: pa.Schema
) -> None:
    if not path.stat().st_size:
        return

    table = load_trusted_arrow_file(path)

    untyped_schema = table.schema
    fields = [
        __DEPRECATED_fix_field(
            untyped_schema.field(i),
            (
                None
                if fallback_schema.get_field_index(name) == -1
                else fallback_schema.field(fallback_schema.get_field_index(name))
            ),
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


def call_fetch(fetch: Callable, request: ttypes.FetchRequest) -> ttypes.FetchResult:
    """Call `fetch()` and validate the result.

    Module code may contain errors. This function and `fetch()` should strive
    to raise developer-friendly errors in the case of bugs -- including
    unexpected input.
    """
    # thrift => pandas
    basedir = Path(request.basedir)
    params: Dict[str, Any] = thrift_params_to_arrow(request.params, basedir).params
    secrets: Dict[str, Any] = thrift_raw_params_to_arrow(request.secrets).params
    if request.input_table_parquet_filename is None:
        input_table_parquet_path = None
    else:
        input_table_parquet_path = basedir / request.input_table_parquet_filename
    if request.last_fetch_result is None:
        last_fetch_result = None
    else:
        last_fetch_result = thrift_fetch_result_to_arrow(
            request.last_fetch_result, basedir
        )
    output_path = basedir / request.output_filename

    result = fetch(
        params=params,
        secrets=secrets,
        last_fetch_result=last_fetch_result,
        input_table_parquet_path=input_table_parquet_path,
        output_path=output_path,
    )

    return arrow_fetch_result_to_thrift(result)


def call_render(render: Callable, request: ttypes.RenderRequest) -> ttypes.RenderResult:
    basedir = Path(request.basedir)
    input_path = basedir / request.input_filename
    table, columns = load_trusted_arrow_file_with_columns(input_path)
    params = thrift_params_to_arrow(request.params, basedir).params
    if request.fetch_result is None:
        fetch_result = None
    else:
        fetch_result = thrift_fetch_result_to_arrow(request.fetch_result, basedir)
    output_path = basedir / request.output_filename

    raw_result = render(
        table,
        params,
        output_path,
        columns=columns,
        settings=settings,
        tab_name=request.tab.name,
        fetch_result=fetch_result,
    )

    # coerce result
    #
    # TODO omit all this code and rely on Workbench's validation. To do this:
    #
    # 1. Change all modules to return RenderResult
    # 2. Nix this coersion code
    _DEPRECATED_overwrite_to_fix_arrow_table_schema(
        output_path, fallback_schema=table.schema
    )
    if raw_result is None:
        errors = []
    elif isinstance(raw_result, list):
        errors = coerce_RenderError_list(raw_result)
    else:
        raise ValueError("Unhandled raw_result")

    return ttypes.RenderResult(
        errors=[arrow_render_error_to_thrift(e) for e in errors], json="{}"
    )
