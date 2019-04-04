from typing import Awaitable, Callable, Union
from django.contrib.auth.models import User
import pandas as pd
from cjworkbench.types import ProcessResult
from server.modules import utils

_join_type_map = 'outer|inner|outer'.split('|')
_source_column_name = 'Source Workflow'


def render(table, params, *, fetch_result, **kwargs):
    if not fetch_result:
        return table

    if fetch_result.status == 'error':
        return fetch_result.error

    if fetch_result.dataframe.empty:
        return 'The workflow you chose is empty'

    type: int = params['type']
    url: str = params['url'].strip()
    source_columns: bool = params['source_columns']

    try:
        right_id = str(utils.workflow_url_to_id(url))
        concat_table = pd.concat([table, fetch_result.dataframe],
                                 keys=['Current', right_id],
                                 join=_join_type_map[type], sort=False)
    except Exception as err:  # TODO specify which errors
        return str(err.args[0])

    # Default, only includes columns of left table
    if type == 0:
        concat_table = concat_table[table.columns]

    if source_columns:
        # Allow duplicates set to True because sanitize handles name
        # collisions
        source_series = concat_table.index.get_level_values(0)
        concat_table.insert(0, _source_column_name,
                            source_series.values, allow_duplicates=True)
    concat_table.reset_index(drop=True, inplace=True)

    return concat_table

async def fetch(params, *, workflow_id: int,
                get_workflow_owner: Callable[[], Awaitable[User]],
                **kwargs) -> Union[pd.DataFrame, str]:
    url: str = params['url']

    if not url.strip():
        return ProcessResult()

    try:
        other_workflow_id = utils.workflow_url_to_id(url)
    except ValueError as err:
        return ProcessResult(error=str(err))

    return await utils.fetch_external_workflow(
        workflow_id,
        await get_workflow_owner(),
        other_workflow_id
    )
