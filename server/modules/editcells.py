import pandas as pd
import numpy as np
from .moduleimpl import ModuleImpl
import json
import logging
from server.sanitizedataframe import safe_column_to_string

logger = logging.getLogger(__name__)

# This will perform poorly if many values are not convertible
def to_numeric(val):
    try:
        return pd.to_numeric(val)
    except:
        return None

# Change a single cell value, with correct type handling when assigning to a numeric col
#  - if val is a number in string form, convert it to numeric first
#  - if val is a true string, cast the column to all strings first
#
def sanitized_edit_cell(table, colname, row, val):
    ctype = table[colname].dtype

    if ctype == np.int64 or ctype == np.float64:
        val_num = to_numeric(val)
        if val_num is not None:
            table.loc[table.index[row], colname] = val_num  # pandas will upcast int64 col to float64 if needed
        else:
            table[colname] = safe_column_to_string(table[colname])  # convert numbers to string, replacing NaN with ''
            table.loc[table.index[row], colname] = val

    else:
        # Column type will be string (see sanitize_dataframe) so assign directly
        if ctype != np.object:
            logger.warning('Unknown Pandas column type %s in edit cells', str(ctype))

        table.loc[table.index[row], colname] = val



class EditCells(ModuleImpl):

    # Execute our edits. Stored in parameter as a json serialized array that looks like this:
    #  [
    #    { 'row': 3, 'col': 'foo', 'value':'bar' },
    #    { 'row': 6, 'col': 'food', 'value':'sandwich' },
    #    ...
    #  ]
    @staticmethod
    def render(wfm, table):
        def format_error():
            logger.exception("Error decoding edit cells data for " + str(wfm))
            wfm.set_error("Internal error")

        edits_json = wfm.get_param_raw('celledits','custom')

        if edits_json.strip() == '':
            return table

        try:
            edits = json.loads(edits_json)
        except ValueError:
            format_error()
            return table

        # if no edits yet, table is unchanged
        if len(edits) == 0:
            return table

        table2 = table.copy()
        try:
            for ed in edits:
                try:
                    col = ed['col']

                    # silently ignore missing columns, maybe they'll come back
                    if col in table2.columns:
                        sanitized_edit_cell(table2, col, ed['row'], ed['value'])

                except (TypeError, KeyError) as e:
                    format_error()
                    return table

        except KeyError:
            format_error()
            return table        # return unmodified table if bad json

        return table2

