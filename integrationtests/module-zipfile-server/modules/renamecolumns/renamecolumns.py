import itertools
import json
from typing import Dict, List, Tuple
from cjwmodule import i18n
from cjwmodule.util.colnames import Settings, gen_unique_clean_colnames_and_warn


class UserVisibleError(Exception):
    """An error that has an `i18n.I18nMessage` as its first argument"""

    @property
    def i18n_message(self):
        return self.args[0]


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


def _parse_renames(
    renames: Dict[str, str], table_columns: List[str], *, settings: Settings
) -> Tuple[Dict[str, str], List[i18n.I18nMessage]]:
    """
    Convert `renames` into a valid mapping for `table_columns`, plus warnings.

    Ignore any renames to "". That column name is not allowed.

    Return a minimal and valid dict from old colname to new colname.

    `renames` is a dict mapping old colname to new colname. It may contain
    missing origin column names and it may duplicate destination column names.
    The logic to handle this: do _all_ the user's renames at once, and then
    queue extra renames for columns that end up with duplicate names. Those
    extra renames are handled left-to-right (the order of `table_columns`
    matters).
    """
    # "renames.get(c) or c" means:
    # * If renames[c] exists and is "", return c
    # * If renames[c] does not exist, return c
    # * If renames[c] exists and is _not_ "", return renames[c]
    nix_colnames = [c for c in table_columns if (renames.get(c) or c) != c]
    nix_colnames_set = frozenset(nix_colnames)
    existing_colnames = [c for c in table_columns if c not in nix_colnames_set]
    try_new_colnames = [renames[c] for c in table_columns if c in nix_colnames_set]

    new_colnames, errors = gen_unique_clean_colnames_and_warn(
        try_new_colnames, existing_names=existing_colnames, settings=settings
    )
    return {k: v for k, v in zip(nix_colnames, new_colnames)}, errors


def _parse_custom_list(
    custom_list: str, table_columns: List[str], *, settings: Settings
) -> Tuple[Dict[str, str], List[i18n.I18nMessage]]:
    """
    Convert `custom_list` into a valid mapping for `table_columns`.

    Return a minimal and valid dict from old colname to new colname.

    Raise `ValueError` if the user entered too many column names.

    `custom_list` is a textarea filled in by a user, separated by
    commas/newlines. (We prefer newlines, but if the user writes a
    comma-separated list we use commas.) The logic to handle this: do _all_
    the user's renames at once, and then queue extra renames for columns
    that end up with duplicate names. Those extra renames are handled
    left-to-right (the order of `table_columns` matters).
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
        raise UserVisibleError(
            i18n.trans(
                "badParam.custom_list.wrongNumberOfNames",
                "You supplied {n_names, plural, other {# column names} one {# column name}}, "
                "but the table has {n_columns, plural, other {# columns} one {# column}}.",
                {"n_names": len(rename_list), "n_columns": len(table_columns)},
            )
        )

    # Use _parse_renames() logic to consider missing columns and uniquify
    return _parse_renames(renames, table_columns, settings=settings)


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


def render(table, params, *, settings: Settings, input_columns):
    columns = list(table.columns)
    if params["custom_list"]:
        try:
            renames, errors = _parse_custom_list(
                params["list_string"], columns, settings=settings
            )
        except UserVisibleError as err:
            return [err.i18n_message]
    else:
        renames, errors = _parse_renames(params["renames"], columns, settings=settings)

    if not renames:
        return table  # no-op

    return {
        **_do_renames(table, input_columns, renames),
        "errors": errors,
    }


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
