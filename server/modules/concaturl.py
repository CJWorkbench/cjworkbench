from typing import Awaitable, Callable, Union
from django.contrib.auth.models import User
import pandas as pd
from cjworkbench.types import ProcessResult
from server.modules import utils

_JoinTypes = {"input": "outer", "intersection": "inner", "union": "outer"}
_SourceColumnName = "Source Workflow"


def render(table, params, *, fetch_result, **kwargs):
    if not fetch_result:
        return table

    if fetch_result.status == "error":
        return fetch_result.error

    if fetch_result.dataframe.empty:
        return "The workflow you chose is empty"

    columns_from: str = params["columns_from"]
    url: str = params["url"].strip()
    add_source_column: bool = params["add_source_column"]

    try:
        right_id = str(utils.workflow_url_to_id(url))
        concat_table = pd.concat(
            [table, fetch_result.dataframe],
            keys=["Current", right_id],
            join=_JoinTypes[columns_from],
            sort=False,
        )
    except Exception as err:  # TODO specify which errors
        return str(err.args[0])

    # Default, only includes columns of left table
    if columns_from == "input":
        concat_table = concat_table[table.columns]

    if add_source_column:
        # Allow duplicates set to True because sanitize handles name
        # collisions
        source_series = concat_table.index.get_level_values(0)
        concat_table.insert(
            0, _SourceColumnName, source_series.values, allow_duplicates=True
        )
    concat_table.reset_index(drop=True, inplace=True)

    return concat_table


async def fetch(
    params,
    *,
    workflow_id: int,
    get_workflow_owner: Callable[[], Awaitable[User]],
    **kwargs,
) -> Union[pd.DataFrame, str]:
    url: str = params["url"]

    if not url.strip():
        return ProcessResult()

    try:
        other_workflow_id = utils.workflow_url_to_id(url)
    except ValueError as err:
        return ProcessResult(error=str(err))

    return await utils.fetch_external_workflow(
        workflow_id, await get_workflow_owner(), other_workflow_id
    )


def _migrate_params_v0_to_v1(params):
    """
    v0: 'type' indexes into input|intersection|union; 'source_columns' is a
    misleading name.

    v1: 'columns_from' is one of those three values; 'add_source_column' is a
    better name.
    """
    return {
        "url": params["url"],
        "add_source_column": params["source_columns"],
        "version_select": params["version_select"],
        "columns_from": ["input", "intersection", "union"][params["type"]],
    }


def migrate_params(params):
    if "type" in params:
        params = _migrate_params_v0_to_v1(params)
    return params
