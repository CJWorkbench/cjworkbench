# --- Time unit conversion to/from seconds ---
import pandas as pd
from django.contrib.sites.models import Site
from intercom.client import Client
import os
import time

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

# don't convert missing values to the string 'NaN'
def string_or_null(val):
    if pd.isnull(val):
        return ''
    else:
        return str(val)

# Convert all complex-typed rows to strings. Otherwise we cannot do many operations
# including hash_pandas_object() and to_parquet()
def sanitize_dataframe(table):
    # full type list at https://pandas.pydata.org/pandas-docs/stable/generated/pandas.api.types.infer_dtype.html
    allowed_types = ['string', 'floating', 'integer', 'categorical', 'boolean', 'datetime', 'date', 'time']
    types = table.apply(pd.api.types.infer_dtype)
    for idx,val in enumerate(types):
        if val not in allowed_types:
            table.iloc[:,idx] = table.iloc[:,idx].apply(string_or_null)

# It is unbelievable that Django is 10+ years old and doesn't already do this for you
def get_absolute_url(abs_url):
    return 'https://%s%s' % ( Site.objects.get_current().domain, abs_url )


# returns analytics IDs if they are set
def get_intercom_app_id():
    try:
        return os.environ['CJW_INTERCOM_APP_ID']
    except KeyError:
        return None

def get_google_analytics_id():
    try:
        return os.environ['CJW_GOOGLE_ANALYTICS']
    except KeyError:
        return None


intercom_client = None

def log_user_event(user, event, metadata=None):
    if intercom_client == None:
        try:
            token = os.environ['CJW_INTERCOM_ACCESS_TOKEN']
            intercom = Client(personal_access_token=token)
        except KeyError:
            return  # env var not set
        except Exception as e:
            print('Error creating Intercom client: ' + str(e))
            return
    try:
        if metadata is not None:   # api errors if metadata=None. Who does that?
            intercom.events.create(
                event_name=event,
                email=user.email,
                id=user.id,
                created_at=int(time.time()),
                metadata=metadata)
        else:
            intercom.events.create(
                event_name=event,
                email=user.email,
                id=user.id,
                created_at=int(time.time()))
    except Exception as e:
        print("Error logging Intercom event '{}': {}".format(event, str(e)))


