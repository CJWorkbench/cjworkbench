import pandas as pd
import numpy as np
from .moduleimpl import ModuleImpl
import json
from .editcells import to_numeric
from server.utils import safe_column_to_string
import logging


class Refine(ModuleImpl):

    def render(wf_module, table):

        edits_json = wf_module.get_param_raw('edits', 'string')
        column_param = wf_module.get_param_column('column')
        print(column_param)
        if edits_json == '':
            return table

        try:
            edits = json.loads(edits_json)
            # Add a hidden column for facet selection tracking
            select_colname = 'temp_backend_selected'
            table[select_colname] = [True for _ in range(len(table.index))]
            for edit in edits:
                if edit['column'] != column_param:
                    continue
                if edit['type'] == 'change':
                    colname = edit['column']
                    ctype = table[colname].dtype
                    from_val_raw = edit['content']['fromVal']
                    to_val_raw = edit['content']['toVal']
                    if ctype == np.int64 or ctype == np.float64:
                        from_val = to_numeric(from_val_raw)
                        to_val = to_numeric(to_val_raw)
                        if (from_val is not None) and (to_val is not None):
                            # If the "to" facet exists, update the selection status of the "from" facet
                            # to that of the "to" facet.
                            if to_val in table[colname].tolist():
                                to_val_selected = table.loc[table[colname] == to_val, select_colname].tolist()[0]
                                table.loc[table[colname] == from_val, select_colname] = to_val_selected
                            table.loc[table[colname] == from_val, colname] = to_val
                        else:
                            table[colname] = safe_column_to_string(table[colname])
                            # If the "to" facet exists, update the selection status of the "from" facet
                            # to that of the "to" facet.
                            if to_val_raw in table[colname].tolist():
                                to_val_selected = table.loc[table[colname] == to_val_raw, select_colname].tolist()[0]
                                table.loc[table[colname] == from_val_raw, select_colname] = to_val_selected
                            table.loc[table[colname] == from_val_raw, colname] = to_val_raw
                    else:
                        # If the "to" facet exists, update the selection status of the "from" facet
                        # to that of the "to" facet.
                        if to_val_raw in table[colname].tolist():
                            to_val_selected = table.loc[table[colname] == to_val_raw, select_colname].tolist()[0]
                            table.loc[table[colname] == from_val_raw, select_colname] = to_val_selected
                        table.loc[table[colname] == from_val_raw, colname] = to_val_raw
                elif edit['type'] == 'select':
                    colname = edit['column']
                    ctype = table[colname].dtype
                    val_raw = edit['content']['value']
                    if ctype == np.int64 or ctype == np.float64:
                        val = to_numeric(val_raw)
                        if val is not None:
                            table.loc[table[colname] == val, select_colname] = (~table.loc[table[colname] == val, select_colname])
                        else:
                            table[colname] = safe_column_to_string(table[colname])
                            table.loc[table[colname] == val_raw, select_colname] = (~table.loc[table[colname] == val_raw, select_colname])
                    else:
                        table.loc[table[colname] == val_raw, select_colname] = (~table.loc[table[colname] == val_raw, select_colname])
            # Keep only rows where the hidden column has value True
            table = table[table[select_colname]]
            # Drop the hidden column
            table = table.drop(select_colname, 1)
        except:
            raise

        return table
