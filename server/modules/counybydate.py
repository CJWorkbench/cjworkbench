from .moduleimpl import ModuleImpl
import pandas as pd
import datetime

# ---- CountByDate ----
# group column by unique value, discard all other columns

class CountByDate(ModuleImpl):
    # Menu items, must match order in json
    SORT_BY_VALUE = 0
    SORT_BY_FREQ = 1

    def render(wf_module, table):
        col  = wf_module.get_param_column('column')
        sortby = wf_module.get_param_menu_idx('sortby')

        if col == '':
            wf_module.set_error('Please select a column containing dates')
            return table

        if table is None:
            return None

        tc = table.columns

        if col not in table.columns:
            return('There is no column named %s' % col)

        # integer columns, just... no. Never really want to interpret as seconds since 1970
        if table[col].dtype == 'int64':
            return('Column %s does not seem to be dates' % col)

        # parse string as date, pull out day, convert back to string
        try:
            dates = pd.to_datetime(table[col])
        except (ValueError, TypeError):
            return('Column %s does not seem to be dates' % col)

        def safedatestr(date):
            if type(date) == datetime.date:
                return date.strftime('%Y-%m-%d')
            else:
                return ""

        if table[col].dtype == 'int64':
            return('Column %s does not seem to be dates' % col)

        dates = dates.dt.date.apply(lambda x: safedatestr(x))  # reformat dates to strings
        newtab = pd.DataFrame(dates.value_counts(sort=(sortby == CountByDate.SORT_BY_FREQ)))
        newtab.reset_index(level=0, inplace=True) # turn index into a column, or we can't see the column names
        newtab.columns = ['date', 'count']
        if sortby != CountByDate.SORT_BY_FREQ:
            newtab = newtab.sort_values('date')

        return newtab
