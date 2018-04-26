from .moduleimpl import ModuleImpl
import pandas as pd

# ---- SelectColumns ----

class SortFromTable(ModuleImpl):
    def render(wf_module, table):
        sort_col = wf_module.get_param_column('column')
        # NOP if column is not selected
        if sort_col == '':
            return table
        if sort_col not in table.columns:
            wf_module.set_error("Sort column no longer exists. Please select a new column.")
            return table

        # Current options: "String|Number|Date"
        sort_type_idx = int(wf_module.get_param_menu_idx('dtype'))

        # Current options: "Ascending|Descending"
        sort_dir_idx = int(wf_module.get_param_menu_idx('direction'))
        # NOP if we are not sorting at all
        if sort_dir_idx == 0:
            return table
        sort_ascending = (sort_dir_idx == 1)

        # A "constant" for our policy on where "NA" should go
        NA_POS = 'last'

        # A temporary column is created for typecast and sorting in the operations below.
        # This column is removed after the sorting so that sort does not modify the data.
        SORTED_SUFFIX = '___sort___'
        tmp_sort_col = sort_col + SORTED_SUFFIX
        if sort_type_idx == 0:
            # Sort as string
            table[tmp_sort_col] = table[sort_col].astype(str)
        elif sort_type_idx == 1:
            # Sort as number
            table[tmp_sort_col] = pd.to_numeric(table[sort_col], errors='coerce')
        elif sort_type_idx == 2:
            # Sort as datetime
            table[tmp_sort_col] = pd.to_datetime(table[sort_col], errors='coerce')

        table.sort_values(
            by=tmp_sort_col,
            ascending=sort_ascending,
            inplace=True,
            na_position=NA_POS)

        table.drop(columns=[tmp_sort_col], inplace=True)
        table.reset_index(inplace=True, drop=True)

        return table
