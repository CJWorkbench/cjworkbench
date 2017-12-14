# --- Time unit conversion to/from seconds ---
import pandas as pd

time_units = {
    'seconds': 1,
    'minutes': 60,
    'hours': 3600,
    'days': 3600 * 24,
    'weeks': 3600 * 24 * 7
}

time_units_ordered = [ 'weeks', 'days', 'hours', 'minutes', 'seconds' ]

# Translate a count of time units into seconds
def units_to_seconds(count, unit):
    if unit not in time_units:
        raise ValueError('unit must be one of seconds, minutes, hours, days, weeks')
    return count * time_units[unit]

# Converts 600 -> (10, 'minutes')
# Picks largest whole unit.
def seconds_to_count_and_units(seconds):
    for unit in time_units_ordered:
        unit_len = time_units[unit]
        if seconds % unit_len == 0:
            return {'units': unit, 'count': int(seconds/unit_len)}

# Displays the user name depending on what user data
# we have available
def user_display(user):
    if hasattr(user, 'first_name') or hasattr(user, 'last_name'):
        return '%s %s' % (user.first_name, user.last_name)
    elif hasattr(user, 'email'):
        return user.email
    else:
        return 'Anonymous'


# Convert all complex-typed rows to strings. Otherwise we cannot do many operations
# including hash_pandas_object() and to_parquet()
def sanitize_dataframe(table):
    # full type list at https://pandas.pydata.org/pandas-docs/stable/generated/pandas.api.types.infer_dtype.html
    allowed_types = ['string', 'floating', 'integer', 'categorical', 'boolean', 'datetime', 'date', 'time']
    types = table.apply(pd.api.types.infer_dtype)
    for idx,val in enumerate(types):
        if val not in allowed_types:
            table.iloc[:,idx] = table.iloc[:,idx].astype(str)