import logging
import time
from typing import Any, Dict, Iterable, Optional, Tuple

from asgiref.sync import async_to_sync
from django.contrib.auth.models import User
from django.http.request import HttpRequest

from cjwstate import rabbitmq


logger = logging.getLogger(__name__)


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
