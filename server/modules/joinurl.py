from typing import Awaitable, Callable
from django.contrib.auth.models import User
import numpy as np
from pandas.api.types import is_numeric_dtype
from cjworkbench.types import ColumnType, ProcessResult
from server.models import Params
from server.modules import utils
from .utils import parse_multicolumn_param

#------ For now, only load workbench urls

_join_type_map = 'Left|Inner|Right'.lower().split('|')

# Prefixes for column matches (and not keys)
lsuffix = '_source'
rsuffix = '_imported'


def check_key_types(left_dtypes, right_dtypes):
    for key in left_dtypes.index:
        l_type = ColumnType.from_dtype(left_dtypes.loc[key])
        r_type = ColumnType.from_dtype(right_dtypes.loc[key])
        if l_type != r_type:
            raise TypeError(
                f'Types do not match for key column "{key}" ({l_type.name} '
                f'and {r_type.name}). Please use a type conversion module to '
                'make these column types consistent.'
            )


# If column types are numeric but do not match (ie. int and float) cast as float to match
def cast_numerical_types(left_table, right_table, keys):
    for key in keys:
        left_dtype = left_table[key].dtype
        right_dtype = right_table[key].dtype
        if (
            is_numeric_dtype(left_dtype)
            and is_numeric_dtype(right_dtype)
            and left_dtype != right_dtype
        ):
            left_table[key] = left_table[key].astype(np.float64)
            right_table[key] = right_table[key].astype(np.float64)


# Insert new duplicate column next to matching source column for legibility
def sort_columns(og_columns, new_columns):
    result = list(new_columns)
    for column in og_columns:
        new_left = column + lsuffix
        new_right = column + rsuffix
        if new_left in new_columns and new_right in new_columns:
            result.pop(result.index(new_right))
            result.insert(result.index(new_left) + 1, new_right)
    return result


def render(table, params, *, fetch_result, **kwargs):
    if not fetch_result:
        # User hasn't fetched yet
        return ProcessResult()

    if fetch_result.status == 'error':
        return fetch_result

    right_table = fetch_result.dataframe

    key_cols, errs = parse_multicolumn_param(params['colnames'], table)

    if errs:
        return ProcessResult(error=(
            'Key columns not in this workflow: '
            + ', '.join(errs)
        ))

    if not key_cols:
        return ProcessResult(table)

    _, errs = parse_multicolumn_param(params['colnames'], right_table)
    if errs:
        return ProcessResult(error=(
            'Key columns not in target workflow: '
            + ', '.join(errs)
        ))

    join_type_idx: int = params['type']
    join_type = _join_type_map[join_type_idx]
    select_columns: bool = params['select_columns']

    if select_columns:
        # 'importcols' is a str param, but we can parse it anyway. For now.
        # Hack upon hack upon hack.
        import_cols, errs = parse_multicolumn_param(params['importcols'],
                                                    right_table)
        if errs:
            return ProcessResult(error=(
                'Selected columns not in target workflow: '
                + ', '.join(errs)
            ))
        right_table = right_table[key_cols + import_cols]

    try:
        check_key_types(table[key_cols].dtypes,
                        right_table[key_cols].dtypes)
        cast_numerical_types(table, right_table, key_cols)
        new_table = table.join(right_table.set_index(key_cols),
                               on=key_cols, how=join_type,
                               lsuffix=lsuffix, rsuffix=rsuffix)
    except Exception as err:  # TODO catch something specific
        return ProcessResult(error=(str(err)))

    new_table = new_table[sort_columns(table.columns, new_table.columns)]

    return ProcessResult(new_table)


async def fetch(params: Params, *, workflow_id: int,
                get_workflow_owner: Callable[[], Awaitable[User]],
                **kwargs) -> ProcessResult:
    url: str = params['url'].strip()

    if not url:
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
