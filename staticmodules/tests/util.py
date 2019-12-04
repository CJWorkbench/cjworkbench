from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Union


class MockParams:
    @staticmethod
    def factory(**kwargs):
        """Build a MockParams factory with default values.

        Usage:

            P = MockParams.factory(foo=3)
            params = P(bar=2)  # {'foo': 3, 'bar': 2}
        """
        return lambda **d: {**kwargs, **d}


@dataclass(frozen=True)
class MockHttpResponse:
    status_code: int = 200
    """HTTP status code"""

    headers: List[Tuple[str, str]] = field(default_factory=list)
    """List of headers -- including Content-Length, Transfer-Encoding, etc."""

    body: Union[bytes, List[bytes]] = b""
    """
    HTTP response body.

    If this is `bytes` (including the default, `b""`), then `headers` requires
    a `Content-Length`. If this is a `List[bytes]`, then `headers` requires
    `Transfer-Encoding: chunked`.
    """

    @classmethod
    def ok(
        cls, body: bytes = b"", headers: List[Tuple[str, str]] = []
    ) -> MockHttpResponse:
        if isinstance(body, bytes):
            if not any(h[0].upper() == "CONTENT-LENGTH" for h in headers):
                # do not append to `headers`: create a new list
                headers = headers + [("Content-Length", str(len(body)))]
        elif isinstance(body, list):
            if not any(h[0].upper() == "TRANSFER-ENCODING" for h in headers):
                # do not append to `headers`: create a new list
                headers = headers + [("Transfer-Encoding", "chunked")]
        else:
            raise TypeError("body must be bytes or List[bytes]; got %r" % type(body))
        return cls(status_code=200, body=body, headers=headers)
