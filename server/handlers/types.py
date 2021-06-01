from __future__ import annotations
from typing import Any, Dict, Optional, NamedTuple

from cjwstate.models.workflow import Workflow


class HandlerRequest(NamedTuple):
    """A WebSockets request to the server.

    This is akin to an HTTP request: a `request_id` ties a response to the
    request. The server must respond to every request.
    """

    request_id: int
    scope: Dict[str, Any]
    workflow: Workflow
    path: str
    arguments: Dict[str, Any]

    @classmethod
    def parse_json_data(
        cls, scope: Dict[str, Any], workflow: Workflow, data: Dict[str, Any]
    ) -> HandlerRequest:
        """Parse JSON into a Request, or raise ValueError.

        JSON format:

            {
                "requestId": 123,
                "path": "submodule.method",
                "arguments": {"kwarg1": "foo", "kwarg2": "bar"}
            }
        """
        if not isinstance(data, dict):
            raise ValueError("request must be a JSON Object")

        try:
            request_id = int(data["requestId"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("request.requestId must be an integer")

        try:
            path = str(data["path"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("request.path must be a string")

        try:
            arguments = data["arguments"]
        except KeyError:
            arguments = {}
        if not isinstance(arguments, dict):
            raise ValueError("request.arguments must be an Object")

        return cls(request_id, scope, workflow, path, arguments)


class HandlerResponse(NamedTuple):
    """Response destined for the WebSockets client that sent a HandlerRequest."""

    request_id: int
    data: Optional[Dict[str, Any]] = None
    error: str = ""

    def to_dict(self):
        if self.error:
            return {"requestId": self.request_id, "error": self.error}
        else:
            return {"requestId": self.request_id, "data": self.data}


class HandlerError(Exception):
    """Error a handler can raise that is _not_ a bug in the handler."""
