from typing import Any, Dict, Awaitable, Callable
from django.contrib.auth.models import User
import numpy as np
from pandas.api.types import is_numeric_dtype
from cjworkbench.types import ColumnType, ProcessResult
from server.modules import utils

# ------ For now, only load workbench urls

# Prefixes for column matches (and not keys)
lsuffix = "_source"
rsuffix = "_imported"


def parse_multicolumn_param(value, table):
    """
    Get (valid_colnames, invalid_colnames) lists in `table`.

    It's easy for a user to select a missing column: just add a rename
    or column-select before the module that selected a valid column.

    Columns will be ordered as they are ordered in `table`.

    XXX this function is _weird_. By the time a module can call it, Workbench
    has _already_ nixed missing columns. So `invalid_colnames` will be empty
    unless `table` isn't the module's input table.
    """
    cols = value.split(",")
    cols = [c.strip() for c in cols if c.strip()]

    table_columns = list(table.columns)

    valid = [c for c in table.columns if c in cols]
    invalid = [c for c in cols if c not in table_columns]

    return (valid, invalid)


def check_key_types(left_dtypes, right_dtypes):
    for key in left_dtypes.index:
        l_type = ColumnType.class_from_dtype(left_dtypes.loc[key])
        r_type = ColumnType.class_from_dtype(right_dtypes.loc[key])
        if l_type != r_type:
            raise TypeError(
                f'Types do not match for key column "{key}" ({l_type().name} '
                f"and {r_type().name}). Please use a type conversion module to "
                "make these column types consistent."
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
        return table

    if fetch_result.status == "error":
        return fetch_result.error

    right_table = fetch_result.dataframe

    key_cols = params["colnames"]
    if not key_cols:
        return table

    missing_in_right_table = [
        c for c in params["colnames"] if c not in right_table.columns
    ]

    if missing_in_right_table:
        return "Key columns not in target workflow: " + ", ".join(
            missing_in_right_table
        )

    join_type = params["type"]
    select_columns: bool = params["select_columns"]

    if select_columns:
        # 'importcols' is a str param, but we can parse it anyway. For now.
        # Hack upon hack upon hack.
        import_cols, errs = parse_multicolumn_param(params["importcols"], right_table)
        if errs:
            return "Selected columns not in target workflow: " + ", ".join(errs)
        right_table = right_table[key_cols + import_cols]

    try:
        check_key_types(table[key_cols].dtypes, right_table[key_cols].dtypes)
        cast_numerical_types(table, right_table, key_cols)
        new_table = table.join(
            right_table.set_index(key_cols),
            on=key_cols,
            how=join_type,
            lsuffix=lsuffix,
            rsuffix=rsuffix,
        )
    except Exception as err:  # TODO catch something specific
        return str(err)

    new_table = new_table[sort_columns(table.columns, new_table.columns)]
    new_table.reset_index(drop=True, inplace=True)

    return new_table


async def fetch(
    params: Dict[str, Any],
    *,
    workflow_id: int,
    get_workflow_owner: Callable[[], Awaitable[User]],
    **kwargs,
) -> ProcessResult:
    url: str = params["url"].strip()

    if not url:
        return None

    try:
        other_workflow_id = utils.workflow_url_to_id(url)
    except ValueError as err:
        return ProcessResult(error=str(err))

    return await utils.fetch_external_workflow(
        workflow_id, await get_workflow_owner(), other_workflow_id
    )


def _migrate_params_v0_to_v1(params):
    """
    v0: 'type' is index into left|inner|right. v1: 'type' is value.
    """
    return {**params, "type": ["left", "inner", "right"][params["type"]]}


def _migrate_params_v1_to_v2(params):
    """
    v1: 'colnames' is comma-separated str. v2: 'colnames' is List[str].
    """
    return {**params, "colnames": [c for c in params["colnames"].split(",") if c]}


def migrate_params(params):
    if isinstance(params["type"], int):
        params = _migrate_params_v0_to_v1(params)
    if isinstance(params["colnames"], str):
        params = _migrate_params_v1_to_v2(params)
    return params
