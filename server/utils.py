# --- Time unit conversion to/from seconds ---
from django.contrib.sites.models import Site
from intercom.client import Client
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


def get_heap_analytics_id():
    try:
        return os.environ['CJW_HEAP_ANALYTICS_ID']
    except KeyError:
        return None


def _setup_intercom_client():
    try:
        token = os.environ['CJW_INTERCOM_ACCESS_TOKEN']
        return Client(personal_access_token=token)
    except KeyError:
        return  # env var not set
    except Exception as e:
        log_message('Error creating Intercom client: ' + str(e))
        return

_intercom_client = _setup_intercom_client()

def log_user_event(user, event, metadata=None):
    log_message("_intercom_client is '{}'".format(str(_intercom_client)))
    log_message("Logging Intercom event '{}' with metadata {}".format(event, str(metadata)))
    if _intercom_client is not None:
        try:
            if metadata is not None:   # api errors if metadata=None. Who does that?
                _intercom_client.events.create(
                    event_name=event,
                    email=user.email,
                    user_id=user.id,
                    created_at=int(time.time()),
                    metadata=metadata)
            else:
                _intercom_client.events.create(
                    event_name=event,
                    email=user.email,
                    user_id=user.id,
                    created_at=int(time.time()))
        except Exception as e:
            log_message("Error logging Intercom event '{}': {}".format(event, str(e)))


