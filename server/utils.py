# --- Time unit conversion to/from seconds ---
import pandas as pd
from django.contrib.sites.models import Site

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

# Convert all complex-typed rows to strings. Otherwise we cannot do many operations
# including hash_pandas_object() and to_parquet()
def sanitize_dataframe(table):
    # full type list at https://pandas.pydata.org/pandas-docs/stable/generated/pandas.api.types.infer_dtype.html
    allowed_types = ['string', 'floating', 'integer', 'categorical', 'boolean', 'datetime', 'date', 'time']
    types = table.apply(pd.api.types.infer_dtype)
    for idx,val in enumerate(types):
        if val not in allowed_types:
            table.iloc[:,idx] = table.iloc[:,idx].astype(str)

# It is unbelievable that Django is 10+ years old and doesn't already do this for you
def get_absolute_url(abs_url):
    return 'https://%s%s' % ( Site.objects.get_current().domain, abs_url )
