import logging
import time
import json


Iso8601DateFormat = "%Y-%m-%dT%H:%M:%S"


class JsonFormatter(logging.Formatter):
    """Logger tuned for StackDriver.

    Docs:
    - https://cloud.google.com/error-reporting/docs/formatting-error-messages
    - https://cloud.google.com/logging/docs/reference/v2/rest/v2/LogEntry

    In particular, be certain that:

    * "severity" is valid (so StackDriver pulls it out of "jsonPayload")
    * "sourceLocation" is valid (so StackDriver pulls it out of "jsonPayload")
    * "message" is set

    TODO tie in the HttpRequest.
    """

    # override
    def format(self, record):
        time_struct = time.gmtime(record.created)
        timestamp = time.strftime(Iso8601DateFormat, time_struct) + (
            ".%03dZ" % record.msecs
        )

        return json.dumps(
            {
                "severity": record.levelname,
                "timestamp": timestamp,
                "sourceLocation": {
                    "file": record.pathname,
                    "line": record.lineno,
                    "function": record.funcName,
                },
                "processId": record.process,
                "threadId": record.thread,
                "module": record.module,
                "message": super().format(record),
            }
        )
