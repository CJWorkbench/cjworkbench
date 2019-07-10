from typing import List
import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype, is_datetime64_dtype


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
                "args": ["converttotext", {"colnames": ",".join(to_convert)}],
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
    varcol = table[varcolname]
    if varcol.dtype != object and not hasattr(varcol, "cat"):
        error = (
            'Column "%s" was auto-converted to Text because column names must '
            "be text." % varcolname
        )
        quick_fixes = [
            {
                "text": 'Convert "%s" to text' % varcolname,
                "action": "prependModule",
                "args": ["converttotext", {"colnames": varcolname}],
            }
        ]
        na = varcol.isnull()
        varcol = varcol.astype(str)
        varcol[na] = np.nan
        table[varcolname] = varcol
    else:
        error = None
        quick_fixes = None

    table.set_index(keycolnames + [varcolname], inplace=True, drop=True)
    if np.any(table.index.duplicated()):
        return "Cannot reshape: some variables are repeated"

    table = table.unstack()
    table.columns = [col[-1] for col in table.columns.values]
    table.reset_index(inplace=True)

    if error is not None:
        return {"dataframe": table, "error": error, "quick_fixes": quick_fixes}
    else:
        return table


def render(table, params):
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
        # We assume that the first column is going to be the new header row
        # Use the content of the first column as the new headers
        # We set the first column header to 'New Column'. Using the old header
        # is confusing.

        # Check if Column Header Exists in Column
        new_columns = table[table.columns[0]].astype(str).tolist()

        new_colname_prefix = "New Column"
        new_colname = new_colname_prefix
        suffix = 1
        while new_colname in new_columns:
            new_colname = f"{new_colname_prefix}_{str(suffix)}"
            if new_colname not in new_columns:
                break
            suffix += 1
        new_columns = [new_colname] + new_columns
        index_col = table.columns[0]
        # Transpose table, reset index and correct column names
        table = table.set_index(index_col).transpose()
        # Clear columns in case CategoricalIndex dtype
        table.columns = [""] * len(table.columns)
        table = table.reset_index()
        table.columns = new_columns

    return table


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
