# --- Time unit conversion to/from seconds ---
import io
import os
import time
import sys
import logging
import tempfile
from typing import Any, Dict, Optional
from django.contrib.sites.models import Site
from django.http.request import HttpRequest
from intercom.client import Client


def get_absolute_url(abs_url):
    return 'https://%s%s' % (Site.objects.get_current().domain, abs_url)


# --- Time conversion ---

_time_units = {
    'seconds': 1,
    'minutes': 60,
    'hours': 3600,
    'days': 3600 * 24,
    'weeks': 3600 * 24 * 7
}

_time_units_ordered = ['weeks', 'days', 'hours', 'minutes', 'seconds']


# Translate a count of time units into seconds
def units_to_seconds(count, unit):
    if unit not in _time_units:
        raise ValueError(
            'unit must be one of seconds, minutes, hours, days, weeks'
        )
    return count * _time_units[unit]


# Converts 600 -> (10, 'minutes')
# Picks largest whole unit.
def seconds_to_count_and_units(seconds):
    for unit in _time_units_ordered:
        unit_len = _time_units[unit]
        if seconds % unit_len == 0:
            return {'units': unit, 'count': int(seconds / unit_len)}


# --- Logging ---

def _setup_console_logger():
    formatter = logging.Formatter(
        fmt='[%(asctime)s.%(msecs)03d %(process)d-%(thread)X] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
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
# TODO move these env-variable handlers to settings.py
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


class NullIntercomClient:
    class Events:
        def create(self, **kwargs):
            log_message(
                'Error logging Intercom event: client not initialized '
                '(bad CJW_INTERCOM_ACCESS_TOKEN?)'
            )

    def __init__(self):
        self.events = NullIntercomClient.Events()


def _setup_intercom_client():
    try:
        token = os.environ['CJW_INTERCOM_ACCESS_TOKEN']
        return Client(personal_access_token=token)
    except KeyError:
        return NullIntercomClient()
    except Exception as e:
        log_message('Error creating Intercom client: ' + str(e))
        return NullIntercomClient()


_intercom_client = _setup_intercom_client()


def log_user_event(request: HttpRequest, event: str,
                   metadata=Optional[Dict[str, Any]]) -> None:
    if request.META.get('HTTP_DNT', '0') == '1':
        # Don't be evil. The user has specifically asked to _not_ be tracked.
        #
        # That should maybe include logs? Let's obfuscate and not show the
        # event or user name.
        log_message('Not logging an event because of DNT header')
        return

    if '/lessons/' in request.META.get('HTTP_REFERER', ''):
        # https://www.pivotaltracker.com/story/show/160041803
        log_message(f"Not logging event '{event}' because it is from a lesson")
        return

    if not request.user.is_authenticated:
        # Intercom has the notion of "leads", but we're basically doomed if we
        # try to associate each request with a potential lead. Our whole point
        # in using Intercom is so we _don't_ need to do that.
        #
        # Also, as of 2018-08-28, virtually all leads sign up and become users
        # anyway. We aren't missing out on users or events in practice.
        #
        # And lest we forget: Intercom is about tracking _users_, not _clicks_.
        # It may be nice to see the whole story of an anonymous user creating a
        # workflow, but Intercom isn't made to do that.
        log_message(f"Not logging event '{event}' for anonymous user")
        return

    log_message(f"Logging Intercom event '{event}' with metadata {metadata}")

    email = request.user.email
    user_id = request.user.id

    if not metadata:
        metadata = {}

    try:
        _intercom_client.events.create(
            event_name=event,
            email=email,
            user_id=user_id,
            created_at=int(time.time()),
            metadata=metadata
        )
    except Exception as err:
        log_message(f"Error logging Intercom event '{event}': {err}")


class TempfileBackedReader(io.RawIOBase):
    """
    Wrapper around a stream that permits seeking backwards.

    Usage:

        with urlopen('http://example.org') as streamio:
            with TempfileBackedReader(streamio) as tempio:
                with io.BufferedReader(tempio) as bufio:
                    bufio.read(10)  # reads from stream
                    bufio.seek(0)
                    bufio.read(20)  # reads from tempfile and stream

    This implementation currently does not support seeking anywhere other than
    the beginning of the file.
    """
    def __init__(self, raw: io.IOBase):
        self.raw = raw

        # tempfile will be removed from disk when Python garbage-collects
        # self._tempfile.
        self._tempfile = tempfile.TemporaryFile()

        self._position = 0  # position in self.raw
        self._tempfile_write_position = 0  # always == n bytes read from raw

    def seekable(self):
        return True

    def writable(self):
        return False

    def readable(self):
        return True

    def close(self):
        """Deletes the tempfile and does NOT close self.raw."""
        self._tempfile.close()
        super().close()

    def _raw_readinto(self, b) -> int:
        """
        Read bytes from the raw source, spooling into the tempfile and `b`.

        Raise AssertionError if our position is not at the end of the tempfile.
        """
        assert self._position == self._tempfile_write_position
        n = self.raw.readinto(b)
        self._tempfile.seek(self._tempfile_write_position)
        self._tempfile.write(b[0:n])
        self._tempfile_write_position += n
        self._position = self._tempfile_write_position
        return n

    def _tempfile_readinto(self, b) -> int:
        """
        Read bytes from the tempfile into `b`.

        Raise AssertionError if the tempfile does not contain enough bytes.
        """
        assert self._position + len(b) <= self._tempfile_write_position
        self._tempfile.seek(self._position)
        n = self._tempfile.readinto(b)
        self._position += n
        return n

    def readinto(self, b) -> int:
        if self._position + len(b) <= self._tempfile_write_position:
            return self._tempfile_readinto(b)
        elif self._position == self._tempfile_write_position:
            return self._raw_readinto(b)
        else:
            n_tempfile = self._tempfile_write_position - self._position
            n1 = self._tempfile_readinto(b[0:n_tempfile])
            assert n1 == n_tempfile
            n2 = self._raw_readinto(b[n_tempfile:])
            return n1 + n2

    def _spool_raw_to_end(self):
        ScanBufferSize = 1024 * 1024
        self._tempfile.seek(self._tempfile_write_position)
        while True:
            b = self.raw.read(ScanBufferSize)
            if b == b'':
                break
            self._tempfile.write(b)
            self._tempfile_write_position += len(b)

    def _spool_raw_to_position(self, position: int):
        ScanBufferSize = 1024 * 1024
        self._tempfile.seek(self._tempfile_write_position)
        remaining = position - self._tempfile_write_position
        while remaining > 0:
            b = self.raw.read(min(ScanBufferSize, remaining))
            if b == b'':
                break
            self._tempfile.write(b)
            self._tempfile_write_position += len(b)
            remaining -= len(b)

    def seek(self, offset, whence=io.SEEK_SET):
        if whence == io.SEEK_END:
            self._spool_raw_to_end()
            self._position = self._tempfile_write_position + offset
        elif whence == io.SEEK_CUR:
            self._spool_raw_to_position(self._position + offset)
            self._position = self._tempfile_write_position + offset
        else:  # SEEK_SET
            self._spool_raw_to_position(offset)
            self._position = offset

        return self._position
