# --- Time unit conversion to/from seconds ---
from django.conf import settings
from django.contrib.sites.models import Site
from intercom.client import Client
import pandas as pd
import os
import time
import sys
import logging


# It is unbelievable that Django is 10+ years old and doesn't already do this for you
def get_absolute_url(abs_url):
    return 'https://%s%s' % ( Site.objects.get_current().domain, abs_url )


# --- Time conversion ---

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


# --- Dataframe sanitization and truncation ---

# convert numbers to string, replacing NaN with '' (naive conversion results in 'Nan' string cells)
def safe_column_to_string(col):
    def string_or_null(val):
        if pd.isnull(val):
            return ''
        else:
            return str(val)
    return col.apply(string_or_null)

# Ensure floats are displayed with as few zeros as possible
def colname_to_str(c):
    if isinstance(c, float):
        return '%g'%c
    else:
        return str(c)

# Convert all complex-typed rows to strings. Otherwise we cannot do many operations
# including hash_pandas_object() and to_parquet()
# Also rename duplicate columns
def sanitize_dataframe(table):
    if table is None:
        return pd.DataFrame()

    # full type list at https://pandas.pydata.org/pandas-docs/stable/generated/pandas.api.types.infer_dtype.html
    allowed_types = ['string', 'floating', 'integer', 'categorical', 'boolean', 'datetime', 'date', 'time']
    types = table.apply(pd.api.types.infer_dtype)
    for idx,val in enumerate(types):
        if val not in allowed_types:
            table.iloc[:,idx] = safe_column_to_string(table.iloc[:,idx])

    # force string column names, and uniquify by appending a number
    newcols = []
    for item in table.columns:
        counter = 0
        newitem = colname_to_str(item)
        while newitem in newcols:
            counter += 1
            newitem = newitem + '_' + str(counter)
        newcols.append(newitem)
    table.columns = newcols

    return table


# Limit table to maximum allowable number of rows. Returns true if we clipped it down
def truncate_table_if_too_big(df):
    nrows = len(df)
    if nrows > settings.MAX_ROWS_PER_TABLE:
        df.drop(range(settings.MAX_ROWS_PER_TABLE, nrows), inplace=True)
        return True
    else:
        return False


# --- Logging ---

def _setup_console_logger():
    formatter = logging.Formatter(fmt='[%(asctime)s.%(msecs)03d %(process)d-%(thread)X] %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')
    screen_handler = logging.StreamHandler(stream=sys.stdout)
    screen_handler.setFormatter(formatter)
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(screen_handler)

    return logger

_console_logger = _setup_console_logger()

def get_console_logger():
    return _console_logger

def log_message(msg):
    _console_logger.debug(msg)

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


def _setup_intercom_client():
    try:
        token = os.environ['CJW_INTERCOM_ACCESS_TOKEN']
        intercom_cl = Client(personal_access_token=token)
    except KeyError:
        return  # env var not set
    except Exception as e:
        log_message('Error creating Intercom client: ' + str(e))
        return

_intercom_client = _setup_intercom_client()

def log_user_event(user, event, metadata=None):
    if _intercom_client is not None:
        try:
            if metadata is not None:   # api errors if metadata=None. Who does that?
                _intercom_client.events.create(
                    event_name=event,
                    email=user.email,
                    id=user.id,
                    created_at=int(time.time()),
                    metadata=metadata)
            else:
                _intercom_client.events.create(
                    event_name=event,
                    email=user.email,
                    id=user.id,
                    created_at=int(time.time()))
        except Exception as e:
            log_message("Error logging Intercom event '{}': {}".format(event, str(e)))


