from .moduleimpl import ModuleImpl
import pandas as pd
import datetime

# ---- CountByDate ----
# group column by unique value, discard all other columns

class CountByDate(ModuleImpl):
    # Menu items, must match order in json
    SORT_BY_VALUE = 0
    SORT_BY_FREQ = 1

    SECOND = 0
    MINUTE = 1
    HOUR = 2
    DAY = 3
    MONTH = 4
    QUARTER = 5
    YEAR = 6

    def render(wf_module, table):
        col  = wf_module.get_param_column('column')
        sortby = wf_module.get_param_menu_idx('sortby')
        groupby = wf_module.get_param_menu_idx('groupby')
        group_options = [
            "%Y-%m-%d %H:%M:%S",  # Seconds
            "%Y-%m-%d %H:%M",  # Minutes
            "%Y-%m-%d %H:00",  # Hours
            "%Y-%m-%d",  # Days
            "%Y-%m",  # Months
            lambda d: "%d Q%d" % (d.year, d.quarter),  # Quarters
            "%Y",  # Years
        ]

        if col == '':
            wf_module.set_error('Please select a column containing dates')
            return table

        if table is None:
            return None

        if col not in table.columns:
            return('There is no column named %s' % col)

        # integer columns, just... no. Never really want to interpret as seconds since 1970
        if table[col].dtype == 'int64':
            return('Column %s does not seem to be dates' % col)

        # convert the date column to actual datetimes
        try:
            table[col] = pd.to_datetime(table[col])
        except (ValueError, TypeError):
            return('Column %s does not seem to be dates' % col)

        if table[col].dtype == 'int64':
            return('Column %s does not seem to be dates' % col)

        if groupby is CountByDate.QUARTER:
            table['groupcol'] = table[col].apply(group_options[groupby])
        else:
            table['groupcol'] = table[col].dt.strftime(group_options[groupby])

        newtab = pd.DataFrame(table.groupby(table['groupcol']).size())

        newtab.reset_index(level=0, inplace=True)  # turn index into a column, or we can't see the column names
        newtab.columns = ['date', 'count']

        if sortby != CountByDate.SORT_BY_FREQ:
            newtab = newtab.sort_values('date')
        else:
            newtab = newtab.sort_values('count')

        return newtab
