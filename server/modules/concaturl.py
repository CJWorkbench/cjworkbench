from typing import Awaitable, Callable
from django.contrib.auth.models import User
import pandas as pd
from cjworkbench.types import ProcessResult
from server.modules import utils

_join_type_map = 'outer|inner|outer'.split('|')
_source_column_name = 'Source Workflow'


def render(table, params, *, fetch_result, **kwargs):
    if not fetch_result:
        return ProcessResult(table)

    if fetch_result.status == 'error':
        return ProcessResult(table, error=fetch_result.error)

    if fetch_result.dataframe.empty:
        return ProcessResult(table,
                             error='The workflow you chose is empty')

    type: int = params['type']
    url: str = params['url'].strip()
    source_columns: bool = params['source_columns']

    try:
        right_id = str(utils.workflow_url_to_id(url))
        concat_table = pd.concat([table, fetch_result.dataframe],
                                 keys=['Current', right_id],
                                 join=_join_type_map[type], sort=False)
    except Exception as err:  # TODO specify which errors
        return ProcessResult(table, error=str(err.args[0]))

    # Default, only includes columns of left table
    if type == 0:
        concat_table = concat_table[table.columns]

    if source_columns:
        # Allow duplicates set to True because sanitize handles name
        # collisions
        source_series = concat_table.reset_index()['level_0']
        concat_table.insert(0, _source_column_name,
                            source_series.values, allow_duplicates=True)

    return ProcessResult(concat_table)

async def fetch(params, *, workflow_id: int,
                get_workflow_owner: Callable[[], Awaitable[User]],
                **kwargs) -> ProcessResult:
    url: str = params['url']

    if not url.strip():
        return None

    try:
        other_workflow_id = utils.workflow_url_to_id(url)
    except ValueError as err:
        return ProcessResult(error=str(err))

    return await utils.fetch_external_workflow(
        workflow_id,
        await get_workflow_owner(),
        other_workflow_id
    )
