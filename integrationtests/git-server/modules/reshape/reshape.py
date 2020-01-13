from typing import Iterator, List, Set
import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype, is_datetime64_dtype


MAX_N_COLUMNS = 100


def wide_to_long(table: pd.DataFrame, colname: str) -> pd.DataFrame:
    # Check all values are the same type
    value_table = table[set(table.columns).difference([colname])]

    if value_table.empty:
        # Avoids 'No objects to concatenate' when colname is categorical and
        # there are no values or other columns
        return pd.DataFrame({colname: [], "variable": [], "value": []}, dtype=str)

    value_dtypes = value_table.dtypes
    are_numeric = value_dtypes.map(is_numeric_dtype)
    are_datetime = value_dtypes.map(is_datetime64_dtype)
    are_text = ~are_numeric & ~are_datetime
    if not are_numeric.all() and not are_datetime.all() and not are_text.all():
        # Convert mixed values so they're all text. Values must all be the same
        # type.
        to_convert = value_table.columns[~are_text]
        na = table[to_convert].isna()
        table.loc[:, to_convert] = table[to_convert].astype(str)
        table.loc[:, to_convert][na] = np.nan

        cols_str = ", ".join(f'"{c}"' for c in to_convert)
        error = (
            f"Columns {cols_str} were auto-converted to Text because the "
            "value column cannot have multiple types."
        )
        quick_fixes = [
            {
                "text": f"Convert {cols_str} to text",
                "action": "prependModule",
                "args": ["converttotext", {"colnames": list(to_convert)}],
            }
        ]
    else:
        error = ""
        quick_fixes = []

    table = pd.melt(table, id_vars=[colname])
    table.sort_values(colname, inplace=True)
    table.reset_index(drop=True, inplace=True)

    if error:
        return {"dataframe": table, "error": error, "quick_fixes": quick_fixes}
    else:
        return table


def long_to_wide(
    table: pd.DataFrame, keycolnames: List[str], varcolname: str
) -> pd.DataFrame:
    warnings = []
    quick_fixes = []

    varcol = table[varcolname]
    if varcol.dtype != object and not hasattr(varcol, "cat"):
        # Convert to str, in-place
        warnings.append(
            (
                'Column "%s" was auto-converted to Text because column names '
                "must be text."
            )
            % varcolname
        )
        quick_fixes.append(
            {
                "text": 'Convert "%s" to text' % varcolname,
                "action": "prependModule",
                "args": ["converttotext", {"colnames": [varcolname]}],
            }
        )
        na = varcol.isnull()
        varcol = varcol.astype(str)
        varcol[na] = np.nan
        table[varcolname] = varcol

    # Remove empty values, in-place. Empty column headers aren't allowed.
    # https://www.pivotaltracker.com/story/show/162648330
    empty = varcol.isin([np.nan, pd.NaT, None, ""])
    n_empty = np.count_nonzero(empty)
    if n_empty:
        if n_empty == 1:
            text_empty = "1 input row"
        else:
            text_empty = "{:,d} input rows".format(n_empty)
        warnings.append('%s with empty "%s" were removed.' % (text_empty, varcolname))
        table = table[~empty]
        table.reset_index(drop=True, inplace=True)

    table.set_index(keycolnames + [varcolname], inplace=True, drop=True)
    if np.any(table.index.duplicated()):
        return "Cannot reshape: some variables are repeated"
    if len(table.columns) == 0:
        return (
            "There is no Value column. "
            "All but one table column must be a Row or Column variable."
        )
    if len(table.columns) > 1:
        return (
            "There are too many Value columns. "
            "All but one table column must be a Row or Column variable. "
            "Please drop extra columns before reshaping."
        )

    table = table.unstack()
    table.columns = [col[-1] for col in table.columns.values]
    table.reset_index(inplace=True)

    if warnings:
        return {
            "dataframe": table,
            "error": "\n".join(warnings),
            "quick_fixes": quick_fixes,
        }
    else:
        return table


def render(table, params, *, input_columns):
    dir = params["direction"]
    colname = params["colnames"]  # bad param name! It's single-column
    varcol = params["varcol"]

    # no columns selected and not transpose, NOP
    if not colname and dir != "transpose":
        return table

    if dir == "widetolong":
        return wide_to_long(table, colname)

    elif dir == "longtowide":
        if not varcol:
            # gotta have this parameter
            return table

        keys = [colname]

        has_second_key = params["has_second_key"]
        # If second key is used and present, append it to the list of columns
        if has_second_key:
            second_key = params["second_key"]
            if second_key in table.columns:
                keys.append(second_key)

        if varcol in keys:
            return "Cannot reshape: column and row variables must be different"

        return long_to_wide(table, keys, varcol)

    elif dir == "transpose":
        return transpose(
            table,
            # Backwards-compat because we published it like this way back when
            {"firstcolname": "New Column"},
            input_columns=input_columns,
        )


def _migrate_params_v0_to_v1(params):
    # v0: menu item indices. v1: menu item labels
    v1_dir_items = ["widetolong", "longtowide", "transpose"]
    params["direction"] = v1_dir_items[params["direction"]]
    return params


def migrate_params(params):
    # Convert numeric direction parameter to string labels, if needed
    if isinstance(params["direction"], int):
        params = _migrate_params_v0_to_v1(params)

    return params


# COPY/PASTE from the `transpose` module.
# EDIT WITH THESE STEPS ONLY:
# 1. Find the bug in the `transpose` module. Unit-test it; fix; deploy.
# 2. Copy/paste the `transpose` module's "render()" method here.
# 3. Rename `render(...)` to `transpose(table, params)`
def transpose(table, params, *, input_columns):
    warnings = []
    colnames_auto_converted_to_text = []

    if len(table) > MAX_N_COLUMNS:
        table = table.truncate(after=MAX_N_COLUMNS - 1)
        warnings.append(
            f"We truncated the input to {MAX_N_COLUMNS} rows so the "
            "transposed table would have a reasonable number of columns."
        )

    if not len(table.columns):
        # happens if we're the first module in the module stack
        return pd.DataFrame()

    # If user does not supply a name (default), use the input table's first
    # column name as the output table's first column name.
    first_colname = params["firstcolname"].strip() or table.columns[0]

    column = table.columns[0]
    headers_series = table[column]
    table.drop(column, axis=1, inplace=True)

    # Ensure headers are string. (They will become column names.)
    if input_columns[column].type != "text":
        warnings.append(f'Headers in column "A" were auto-converted to text.')
        colnames_auto_converted_to_text.append(column)

    # Regardless of column type, we want to convert to str. This catches lots
    # of issues:
    #
    # * Column names shouldn't be a CategoricalIndex; that would break other
    #   Pandas functions. See https://github.com/pandas-dev/pandas/issues/19136
    # * nulls should be converted to '' instead of 'nan'
    # * Non-str should be converted to str
    # * `first_colname` will be the first element (so we can enforce its
    #   uniqueness).
    #
    # After this step, `headers` will be a List[str]. "" is okay for now: we'll
    # catch that later.
    na = headers_series.isna()
    headers_series = headers_series.astype(str)
    headers_series[na] = ""  # Empty values are all equivalent
    headers_series[headers_series.isna()] = ""
    headers = headers_series.tolist()
    headers.insert(0, first_colname)
    non_empty_headers = [h for h in headers if h]

    # unique_headers: all the "valuable" header names -- the ones we won't
    # rename any duplicate/empty headers to.
    unique_headers = set(headers)

    if "" in unique_headers:
        warnings.append(
            f'We renamed some columns because the input column "{column}" had '
            "empty values."
        )
    if len(non_empty_headers) != len(unique_headers - set([""])):
        warnings.append(
            f'We renamed some columns because the input column "{column}" had '
            "duplicate values."
        )

    headers = list(_uniquize_colnames(headers, unique_headers))

    table.index = headers[1:]

    input_types = set(c.type for c in input_columns.values() if c.name != column)
    if len(input_types) > 1:
        # Convert everything to text before converting. (All values must have
        # the same type.)
        to_convert = [c for c in table.columns if input_columns[c].type != "text"]
        colnames_auto_converted_to_text.extend(to_convert)
        if len(to_convert) == 1:
            start = f'Column "{to_convert[0]}" was'
        else:
            colnames = ", ".join(f'"{c}"' for c in to_convert)
            start = f"Columns {colnames} were"
        warnings.append(
            f"{start} auto-converted to Text because all columns must have "
            "the same type."
        )

        for colname in to_convert:
            # TODO respect column formats ... and nix the quick-fix?
            na = table[colname].isnull()
            table[colname] = table[colname].astype(str)
            table[colname][na] = np.nan

    # The actual transpose
    ret = table.T
    # Set the name of the index: it will become the name of the first column.
    ret.index.name = first_colname
    # Make the index (former colnames) a column
    ret.reset_index(inplace=True)

    if warnings and colnames_auto_converted_to_text:
        colnames = ", ".join(f'"{c}"' for c in colnames_auto_converted_to_text)
        return {
            "dataframe": ret,
            "error": "\n".join(warnings),
            "quick_fixes": [
                {
                    "text": f"Convert {colnames} to text",
                    "action": "prependModule",
                    "args": [
                        "converttotext",
                        {"colnames": ",".join(colnames_auto_converted_to_text)},
                    ],
                }
            ],
        }
    if warnings:
        return (ret, "\n".join(warnings))
    else:
        return ret


def _uniquize_colnames(
    colnames: Iterator[str], never_rename_to: Set[str]
) -> Iterator[str]:
    """
    Rename columns to prevent duplicates or empty column names.

    The algorithm: iterate over each `colname` and add to an internal "seen".
    When we encounter a colname we've seen, append " 1", " 2", " 3", etc. to it
    until we encounter a colname we've never seen that is not in
    `never_rename_to`.
    """
    seen = set()
    for colname in colnames:
        force_add_number = False
        if not colname:
            colname = "unnamed"
            force_add_number = "unnamed" in never_rename_to
        if colname in seen or force_add_number:
            for i in range(1, 999999):
                try_colname = f"{colname} {i}"
                if try_colname not in seen and try_colname not in never_rename_to:
                    colname = try_colname
                    break

        seen.add(colname)
        yield colname


# END copy/paste
