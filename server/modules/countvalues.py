from .moduleimpl import ModuleImpl
import pandas as pd

# ---- CountValue ----
# group column by unique value, discard all other columns

class CountValues(ModuleImpl):
    def render(wf_module, table):
        if table is None:
            return None

        col  = wf_module.get_param_column('column')
        sortby = wf_module.get_param_menu_string('sortby')

        if col == '':
            return('Please select a column')

        if col not in table.columns:
            return('There is no column named %s' % col)

        newtab = pd.DataFrame(table[col].value_counts(sort=(sortby == 'Frequency')))
        newtab.reset_index(level=0, inplace=True) # turn index into a column, or we can't see the column names
        newtab.columns = [col, 'count']

        return newtab
