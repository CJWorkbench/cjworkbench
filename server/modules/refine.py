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

        try:
            edits = json.loads(edits_json)
            for edit in edits:
                colname = edit['column']
                ctype = table[colname].dtype
                if ctype == np.int64 or ctype == np.float64:
                    from_val = to_numeric(edit['fromVal'])
                    to_val = to_numeric(edit['toVal'])
                    if (from_val is not None) and (to_val is not None):
                        table.loc[table[colname] == from_val, colname] = to_val
                    else:
                        table[colname] = safe_column_to_string(table[colname])
                        table.loc[table[colname] == edit['fromVal'], colname] = edit['toVal']
                else:
                    table.loc[table[colname] == edit['fromVal'], colname] = edit['toVal']
        except:
            pass

        return table
