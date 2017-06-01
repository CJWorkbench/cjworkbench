from .moduleimpl import ModuleImpl
import pandas as pd

# ---- CountByDate ----
# group column by unique value, discard all other columns

class CountByDate(ModuleImpl):
    def render(wf_module, table):
        if table is None:
            return None

        col  = wf_module.get_param_string('column')
        sortby = wf_module.get_param_menu_string('sortby')

        if col == '':
            wf_module.set_error('Please select a column')
            return None     # no columns, no matches

        if col not in table.columns:
            wf_module.set_error('There is no column named %s' % col)
            return None

        # integer columns, just... no. Never really want to interpret as seconds since 1970
        if table[col].dtype == 'int64':
            wf_module.set_error('Column %s does not seem to be dates' % col)
            return None

        # parse string as date, pull out day, convert back to string
        try:
            dates = pd.to_datetime(table[col])
        except ValueError:
            wf_module.set_error('Column %s does not seem to be dates' % col)
            return None

        dates = dates.dt.date.apply(lambda x: x.strftime('%Y-%m-%d'))  # reformat dates to strings
        newtab = pd.DataFrame(dates.value_counts(sort=(sortby == 'Frequency')))
        newtab.reset_index(level=0, inplace=True) # turn index into a column, or we can't see the column names
        newtab.columns = ['date', 'count']
        if sortby != 'Frequency':
            newtab = newtab.sort_values('date')

        return newtab
