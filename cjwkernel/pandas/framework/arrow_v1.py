import datetime
from pathlib import Path
from typing import Callable

import pyarrow as pa
from cjwmodule.types import UploadedFile
from cjwmodule.arrow.types import ArrowRenderResult, TabOutput

from cjwkernel import settings
from cjwkernel.thrift import ttypes
from cjwkernel.types import (
    arrow_render_error_to_thrift,
    pydict_to_thrift_json_object,
    thrift_fetch_result_to_arrow,
    thrift_json_object_to_pydict,
)
from cjwkernel.validate import load_trusted_arrow_file


def call_render(render: Callable, request: ttypes.RenderRequest) -> ttypes.RenderResult:
    basedir = Path(request.basedir)
    table = load_trusted_arrow_file(basedir / request.input_filename)
    params = thrift_json_object_to_pydict(request.params)

    tab_outputs = {
        k: TabOutput(
            tab_name=v.tab_name,
            table=load_trusted_arrow_file(basedir / v.table_filename),
        )
        for k, v in request.tab_outputs.items()
    }

    uploaded_files = {
        k: UploadedFile(
            name=v.name,
            path=(basedir / v.filename),
            uploaded_at=datetime.datetime.utcfromtimestamp(
                v.uploaded_at_timestampus / 1000000.0
            ),
        )
        for k, v in request.uploaded_files.items()
    }

    if request.fetch_result is None:
        fetch_result = None
    else:
        fetch_result = thrift_fetch_result_to_arrow(request.fetch_result, basedir)

    raw_result = render(
        table,
        params,
        settings=settings,
        tab_name=request.tab_name,
        tab_outputs=tab_outputs,
        uploaded_files=uploaded_files,
        fetch_result=fetch_result,
    )

    if not isinstance(raw_result, ArrowRenderResult):
        # Crash. The module author wrote a buggy module.
        raise ValueError(
            "render_arrow_v1() must return a cjwmodule.arrow.types.ArrowRenderResult"
        )

    with pa.ipc.RecordBatchFileWriter(
        basedir / request.output_filename, schema=raw_result.table.schema
    ) as writer:
        writer.write_table(raw_result.table)

    return ttypes.RenderResult(
        errors=[arrow_render_error_to_thrift(e) for e in raw_result.errors],
        json=pydict_to_thrift_json_object(raw_result.json),
    )
