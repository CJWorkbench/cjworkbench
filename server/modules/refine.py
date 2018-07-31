import pandas as pd
import numpy as np
from .moduleimpl import ModuleImpl
from .types import ProcessResult
import json
from server.sanitizedataframe import safe_column_to_string


# This will perform poorly if many values are not convertible
def to_numeric(val):
    try:
        return pd.to_numeric(val)
    except:
        return None


def to_timestamp(val):
    try:
        return pd.Timestamp(val)
    except ValueError:
        return None


select_colname = 'temp_backend_selected'


def do_edit(table, colname, from_val, to_val):
    # Performs an edit on the table in place.
    # If the "to" facet exists, update the selection status of the "from" facet
    # to that of the "to" facet.
    if to_val in table[colname].tolist():
        to_val_selected = table.loc[table[colname] == to_val, select_colname] \
                .tolist()[0]
        table.loc[table[colname] == from_val, select_colname] = to_val_selected
    table.loc[table[colname] == from_val, colname] = to_val


def do_select(table, colname, val):
    # Performs a selection on the table in place.
    table.loc[table[colname] == val, select_colname] \
            = (~table.loc[table[colname] == val, select_colname])


def apply_edit(table, edit):
    colname = edit['column']
    ctype = table[colname].dtype

    if edit['type'] == 'change':
        from_val_raw = edit['content']['fromVal']
        to_val_raw = edit['content']['toVal']
        if ctype == np.int64 or ctype == np.float64:
            from_val = to_numeric(from_val_raw)
            to_val = to_numeric(to_val_raw)
            if (from_val is not None) and (to_val is not None):
                do_edit(table, colname, from_val, to_val)
            else:
                table[colname] = safe_column_to_string(table[colname])
                do_edit(table, colname, from_val, to_val)
        elif ctype == 'datetime64[ns]':
            from_val = to_timestamp(from_val_raw)
            to_val = to_timestamp(to_val_raw)
            if (from_val is not None) and (to_val is not None):
                do_edit(table, colname, from_val, to_val)
            else:
                table[colname] = safe_column_to_string(table[colname])
                do_edit(table, colname, from_val_raw, to_val_raw)
        else:
            do_edit(table, colname, from_val_raw, to_val_raw)
    elif edit['type'] == 'select':
        val_raw = edit['content']['value']
        if ctype == np.int64 or ctype == np.float64:
            val = to_numeric(val_raw)
            if val is not None:
                do_select(table, colname, val)
            else:
                table[colname] = safe_column_to_string(table[colname])
                do_select(table, colname, val_raw)
        elif ctype == 'datetime64[ns]':
            val = to_timestamp(val_raw)
            if val is not None:
                do_select(table, colname, val)
            else:
                table[colname] = safe_column_to_string(table[colname])
                do_select(table, colname, val_raw)
        else:
            do_select(table, colname, val_raw)


class Refine(ModuleImpl):
    def render(wf_module, table):
        # 'refine' holds the edits
        edits_json = wf_module.get_param_raw('refine', 'custom')
        column_param = wf_module.get_param_column('column')
        if edits_json == '':
            return ProcessResult(table)

        # Add a hidden column for facet selection tracking
        # TODO don't.
        table[select_colname] = [True for _ in range(len(table.index))]

        edits = json.loads(edits_json)
        for edit in edits:
            if (edit['column'] != column_param) \
               or (edit['column'] not in table.columns):
                continue

            apply_edit(table, edit)

        # Keep only rows where the hidden column has value True
        table = table[table[select_colname]]
        # Drop the hidden column
        table = table.drop(select_colname, 1)

        return ProcessResult(table)
