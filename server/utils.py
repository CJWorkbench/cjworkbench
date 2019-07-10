import os
import time
import logging
from typing import Any, Dict, Iterable, Optional, Tuple
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.http.request import HttpRequest
from intercom.client import Client
import intercom.errors
import requests.exceptions  # we don't depend on `requests`, but intercom does


logger = logging.getLogger(__name__)


def get_absolute_url(abs_url):
    return "https://%s%s" % (Site.objects.get_current().domain, abs_url)


# --- Logging ---
class NullIntercomClient:
    class Events:
        def create(self, **kwargs):
            logger.info(
                "Error logging Intercom event: client not initialized "
                "(bad CJW_INTERCOM_ACCESS_TOKEN?)"
            )

    def __init__(self):
        self.events = NullIntercomClient.Events()


def _setup_intercom_client():
    try:
        token = os.environ["CJW_INTERCOM_ACCESS_TOKEN"]
        return Client(personal_access_token=token)
    except KeyError:
        return NullIntercomClient()
    except Exception as e:
        logger.info("Error creating Intercom client: " + str(e))
        return NullIntercomClient()


_intercom_client = _setup_intercom_client()


class Headers:
    def __init__(self, data):
        """
        Initialize.

        `data` keys must be all-uppercase, all-ASCII, underscores instead of
        dashes.
        """
        self.data = data

    def get(self, key: str, default: Optional[str]) -> Optional[str]:
        """
        Get a header. `key` must be all-uppercase.

        >>> headers = Headers({'CONTENT_TYPE': 'application/json'})
        >>> headers.get('CONTENT_TYPE', 'application/octet-stream')
        "application/json"
        """
        return self.data.get(key, default)

    @classmethod
    def from_http(cls, http_headers: Iterable[Tuple[bytes, bytes]]):
        """
        Parse Headers from the raw HTTP list.


        """
        data = dict(
            (k.decode("latin1").upper().replace("-", "_"), v.decode("latin1"))
            for k, v in http_headers
        )
        return cls(data)

    @classmethod
    def from_META(cls, meta: Dict[str, str]):
        """Parse Headers from a wsgi environ."""
        data = dict((k, v[5:]) for k, v in meta.items() if k.startswith("HTTP_"))
        for wsgi_special_case in ["CONTENT_TYPE", "CONTENT_LENGTH"]:
            try:
                data[wsgi_special_case] = meta[wsgi_special_case]
            except KeyError:
                pass

        return cls(data)


def _log_user_event(
    user: User, headers: Headers, event: str, metadata: Optional[Dict[str, Any]] = None
) -> None:
    if headers.get("DNT", "0") == "1":
        # Don't be evil. The user has specifically asked to _not_ be tracked.
        #
        # That should maybe include logs? Let's obfuscate and not show the
        # event or user name.
        logger.debug("Not logging an event because of DNT header")
        return

    if "/lessons/" in headers.get("REFERER", ""):
        # https://www.pivotaltracker.com/story/show/160041803
        logger.debug("Not logging event '%s' because it is from a lesson", event)
        return

    if not user.is_authenticated:
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
        logger.debug("Not logging event '%s' for anonymous user", event)
        return

    logger.debug("Logging Intercom event '%s' with metadata %r", event, metadata)

    email = user.email
    user_id = user.id

    if not metadata:
        metadata = {}

    try:
        _intercom_client.events.create(
            event_name=event,
            email=email,
            user_id=user_id,
            created_at=int(time.time()),
            metadata=metadata,
        )
    except (
        intercom.errors.ServiceUnavailableError,
        intercom.errors.ResourceNotFound,
        requests.exceptions.RequestException,
    ) as err:
        # on production, these happen every day or two:
        #
        # intercom.errors.ServiceUnavailableError: Sorry, the API service is
        # temporarily unavailable
        #
        # intercom.errors.ResourceNotFound: User Not Found
        #
        # requests.exceptions.ConnectionError: ('Connection aborted.',
        # RemoteDisconnected('Remote end closed connection without response',))
        #
        # _log_ the problem, but don't logger.exception(): we don't want to
        # receive an email about it.
        logger.info("(known) error logging Intercom event '%s': %r", event, err)
        pass
    except Exception:
        logger.exception("Error logging Intercom event '%s'", event)


def log_user_event_from_request(
    request: HttpRequest, event: str, metadata: Optional[Dict[str, Any]] = None
) -> None:
    return _log_user_event(
        request.user, Headers.from_META(request.META), event, metadata
    )


def log_user_event_from_scope(
    scope: Dict[str, Any], event: str, metadata: Optional[Dict[str, Any]] = None
) -> None:
    return _log_user_event(
        scope["user"], Headers.from_http(scope["headers"]), event, metadata
    )
