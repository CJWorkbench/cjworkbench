import itertools
import json
from typing import Dict, List


def _uniquify(colnames: List[str]):
    """
    Return `colnames`, renaming non-unique names to be unique.

    The logic: walk the list from left to right. When we see a column name,
    for the first time, blacklist it. If we see a blacklisted column name,
    rename it by adding a unique digit and blacklist the new name.
    """
    seen = set()
    ret = []

    for colname in colnames:
        if colname in seen:
            # Modify `colname` by adding a number to it.
            for n in itertools.count():
                try_colname = f"{colname} {n + 1}"
                if try_colname not in seen:
                    colname = try_colname
                    break
        ret.append(colname)
        seen.add(colname)

    return ret


def _parse_renames(renames: Dict[str, str], table_colnames: List[str]):
    """
    Convert `renames` into a valid mapping for `table_colnames`.

    Ignore any renames to "". That column name is not allowed.

    Return a minimal and valid dict from old colname to new colname.

    `renames` is a dict mapping old colname to new colname. It may contain
    missing origin column names and it may duplicate destination column names.
    The logic to handle this: do _all_ the user's renames at once, and then
    queue extra renames for columns that end up with duplicate names. Those
    extra renames are handled left-to-right (the order of `table_colnames`
    matters).
    """
    # "renames.get(c) or c" means:
    # * If renames[c] exists and is "", return c
    # * If renames[c] does not exist, return c
    # * If renames[c] exists and is _not_ "", return renames[c]
    new_colnames = _uniquify([(renames.get(c) or c) for c in table_colnames])
    return {o: n for o, n in zip(table_colnames, new_colnames) if o != n}


def _parse_custom_list(custom_list: str, table_columns: List[str]):
    """
    Convert `custom_list` into a valid mapping for `table_colnames`.

    Return a minimal and valid dict from old colname to new colname.

    Raise `ValueError` if the user entered too many column names.

    `custom_list` is a textarea filled in by a user, separated by
    commas/newlines. (We prefer newlines, but if the user writes a
    comma-separated list we use commas.) The logic to handle this: do _all_
    the user's renames at once, and then queue extra renames for columns
    that end up with duplicate names. Those extra renames are handled
    left-to-right (the order of `table_colnames` matters).
    """
    # Chomp trailing newline, in case the user enters "A,B,C\n".
    custom_list = custom_list.rstrip()

    # Split by newline (preferred) or comma (if the user wants that)
    if "\n" in custom_list:
        split_char = "\n"
    else:
        split_char = ","
    rename_list = [s.strip() for s in custom_list.split(split_char)]

    # Convert to dict
    try:
        renames = {table_columns[i]: s for i, s in enumerate(rename_list) if s}
    except IndexError:
        raise ValueError(
            f"You supplied {len(rename_list)} column names, "
            f"but the table has {len(table_columns)} columns."
        )

    # Use _parse_renames() logic to consider missing columns and uniquify
    return _parse_renames(renames, table_columns)


def _do_renames(table, input_columns, renames):
    # Edit in-place
    table.rename(columns=renames, inplace=True)
    return {
        "dataframe": table,
        # Every new (or overwritten) column name gets a format
        "column_formats": {
            new: input_columns[old].format for old, new in renames.items()
        },
    }


def render(table, params, *, input_columns):
    columns = list(table.columns)
    if params["custom_list"]:
        try:
            renames = _parse_custom_list(params["list_string"], columns)
        except ValueError as err:
            return str(err)
    else:
        renames = _parse_renames(params["renames"], columns)

    if not renames:
        return table  # no-op

    return _do_renames(table, input_columns, renames)


def _migrate_params_v0_to_v1(params):
    """
    v0: params['rename-entries'] is JSON-encoded dict of {old: new}

    v1: params['renames'] is dict of {old: new}
    """
    ret = dict(params)  # copy
    try:
        ret["renames"] = json.loads(ret["rename-entries"])
    except ValueError:
        ret["renames"] = {}
    del ret["rename-entries"]
    return ret


def migrate_params(params):
    if "rename-entries" in params:
        params = _migrate_params_v0_to_v1(params)

    return params
