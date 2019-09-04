# Functions that will appear in a loaded module, unless user code defines the
# functions already.

import json
import os
import pathlib
import tempfile
import pandas as pd
import pyarrow
from typing import Any, Dict
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
    raise NotImplementedError("This module does not define a render() function")


def render_pandas(
    table: pd.DataFrame,
    params: Dict[str, Any],
    tab_name: str,
    input_tabs: Dict[str, ptypes.TabOutput],
) -> ptypes.ProcessResult:
    """
    Call `render()` and validate the result.

    Module authors should not replace this function: they should replace
    `render()` instead.

    This function validates the `render()` return value, to raise a helpful
    ValueError if the module code is buggy.
    """
    raw_result = render(table)
    return ptypes.ProcessResult.coerce(raw_result)  # raise ValueError if invalid


def _arrow_to_pandas(table: pyarrow.Table) -> pd.DataFrame:
    return table.to_pandas(
        date_as_object=False, deduplicate_objects=True, ignore_metadata=True
    )  # TODO ensure dictionaries stay dictionaries


def render_arrow(
    table: types.ArrowTable,
    params: Dict[str, Any],
    tab_name: str,
    input_tabs: Dict[str, types.TabOutput],
    output_path: pathlib.Path,
) -> types.RenderResultOk:
    """
    Render using `cjwkernel.types` data types.

    If outputting Arrow data, write to `output_path`.

    Module authors are encouraged to replace this function, because Arrow
    tables are simpler and more memory-efficient than Pandas tables. This is
    the ideal signature for a "rename columns" module, for instance: Arrow
    can pass data through without consuming excessive RAM.

    This does not validate the render_pandas() return value.
    """
    pandas_table = _arrow_to_pandas(table.table)
    pandas_input_tabs = {k: _arrow_to_pandas(v) for k, v in input_tabs.items()}
    pandas_result: ptypes.ProcessResult = render_pandas(
        pandas_table, params, tab_name, pandas_input_tabs
    )

    return pandas_result.to_arrow(output_path)


def render_thrift(
    input_table: ttypes.ArrowTable,
    params: ttypes.Params,
    tab: ttypes.Tab,
    input_tabs: Dict[str, ttypes.TabOutput],
) -> ttypes.RenderResultOk:
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
    arrow_table = types.ArrowTable.from_thrift(input_table)
    params_dict = json.loads(params.json)
    arrow_input_tabs = {
        k: types.TabOutput.from_thrift(v) for k, v in input_tabs.items()
    }

    fd, filename = tempfile.mkstemp(dir=".")
    os.close(fd)

    arrow_result: types.RenderResultOk = render_arrow(
        arrow_table, params_dict, tab.name, arrow_input_tabs, pathlib.Path(filename)
    )

    return arrow_result.to_thrift()
