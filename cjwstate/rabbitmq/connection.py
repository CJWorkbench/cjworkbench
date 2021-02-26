from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import AsyncContextManager, Awaitable, Callable, Optional

import carehare
import msgpack
from django.conf import settings


logger = logging.getLogger(__name__)


async def connect_with_retry(
    url: str,
    *,
    retries: int = 10,
    backoff_delay: float = 2.0,
    connect_timeout: float = 10.0,
    stop_retrying: Optional[asyncio.Future[None]] = None,
) -> carehare.Connection:
    """Connect to RabbitMQ, retrying if needed and failing in case of disaster.

    The caller should eventually await `retval.close()`.

    Features [tested?]:

    [ ] `retries` argument: if connecting raises `ConnectionError` or
        `asyncio.TimeoutError` repeatedly, `await connecting` will raise the
        error on the `retries`-th attempt.
    [ ] `backoff_delay` argument: sleep 0s before the first retry; thereafter,
        add `backoff_delay` to the sleep amount before sleeping.
    [ ] `connect_timeout` argument: each attempt to connect to RabbitMQ will
        raise `asyncio.TimeoutError` after this duration. (Otherwise, the only
        error will be `ConnectionError` -- but beware: typical firewalls stall
        connections for ages without causing `ConnectionError`.)
    [ ] `stop_retrying` argument: the caller may set this to stop the retry
        mechanism: the "current" attempt (at call time) will be the last one.
        (Its error will be raised or its success will be returned.)
    """
    next_delay = 0.0
    for retry in range(retries):
        try:
            connection = carehare.Connection(url, connect_timeout=connect_timeout)
            await connection.connect()
            return connection
        except (ConnectionError, asyncio.TimeoutError) as err:
            if retry >= retries - 1 or (
                stop_retrying is not None and stop_retrying.done()
            ):
                raise
            else:
                logger.warn(
                    "Failed to connect to RabbitMQ (%s); retrying in %fs",
                    str(err),
                    next_delay,
                )
                await asyncio.sleep(next_delay)  # TODO stop_retrying short-circuit
                next_delay += backoff_delay


_global_stopping: Optional[asyncio.Future[None]] = None
_global_awaitable_connection: Optional[asyncio.Future[carehare.Connection]] = None


async def get_global_connection():
    """Make a best effort to return an active RabbitMQ connection.

    Raise `ConnectionError` or `asyncio.TimeoutError` if we fail. These errors
    indicate catastrophic failure: the server should shut down.

    The returned connection might be unusable if an error occurs at just the
    wrong time. If that's the case, subsequent calls will await a new
    connection.
    """
    if _global_awaitable_connection is None:
        raise RuntimeError(
            "Please call maintain_global_connection() before get_global_connection()"
        )
    return await _global_awaitable_connection


@contextlib.asynccontextmanager
async def open_global_connection() -> AsyncContextManager[carehare.Connection]:
    """Yield a carehare.Connection that is _also_ stored as a global variable.

    The yielded connection will be used by `cjwstate.rabbitmq` methods.

    Raise before yield if the connection could not start.

    Raise during close if the connection could not be closed cleanly.
    """
    global _global_awaitable_connection
    assert _global_awaitable_connection is None

    connection = await connect_with_retry(settings.RABBITMQ_HOST)
    try:
        _global_awaitable_connection = asyncio.Future()
        _global_awaitable_connection.set_result(connection)
        yield connection
    finally:
        await connection.close()
        assert _global_awaitable_connection is not None
        _global_awaitable_connection = None


async def maintain_global_connection(
    on_connect: Optional[Callable[[carehare.Connection], Awaitable[None]]] = None
) -> None:
    """Try to keep `_global_awaitable_connection` as useful as possible.

    Connect repeatedly to the RabbitMQ server. Each time, call
    `on_connect(connection)` and then set `_global_awaitable_connection`.

    Raise `ConnectionError` or `asyncio.TimeoutError` if connection fails after
    many retries. The `_global_awaitable_connection` will also resolve to
    an exception. The caller is responsible for crashing the app if this
    happens.

    Raise any errors `on_connect(connection)` raises.

    Raise `ConnectionError`, `carehare.ConnectionClosedByServer` or
    `carehare.ConnectionClosedByHeartbeatMonitor` if the connection is closed
    abnormally -- but these can only be raised _after_
    calling `stop_global_connection()`. Before that call, instead of raising,
    log the errors and restart connection.

    Anything raised is catastrophic: the caller should ensure the process exits
    with an error code.

    Return if `_global_stopping` is set and we disconnected cleanly.
    """
    global _global_awaitable_connection
    global _global_stopping

    _global_stopping = asyncio.Future()
    while not _global_stopping.done():
        _global_awaitable_connection = asyncio.Future()

        logger.info("Connecting to RabbitMQ")
        try:
            connection = await connect_with_retry(
                settings.RABBITMQ_HOST, stop_retrying=_global_stopping
            )
            _global_awaitable_connection.set_result(connection)
        except (ConnectionError, asyncio.TimeoutError) as err:
            if _global_stopping.done():
                logger.info(
                    "Ignoring RabbitMQ connection error because we're closing: %s",
                    str(err),
                )
                break
            else:
                _global_awaitable_connection.set_exception(err)
                raise  # Somebody needs to shut us down

        logger.info("Connected to RabbitMQ")

        if on_connect is not None:
            await on_connect(connection)  # or raise -- meaning catastrophe

        try:
            # Wait. Ideally, forever.
            await asyncio.wait(
                {connection.closed, _global_stopping},
                return_when=asyncio.FIRST_COMPLETED,
            )
            if not connection.closed.done():
                await connection.close()
        except (
            ConnectionError,
            carehare.ConnectionClosedByServer,
            carehare.ConnectionClosedByHeartbeatMonitor,
        ) as err:
            logger.exception("Abnormal disconnect from RabbitMQ: %s", str(err))
            # Now we'll loop and set a new _global_awaitable_connection.

    _global_stopping = None
    _global_awaitable_connection = None


async def stop_global_connection():
    """Ensure we're disconnected from RabbitMQ.

    This should return cleanly and relatively promptly. The maximum delay is
    roughly `max(connect_timeout, heartbeat*1.5)` seconds.

    Does not raise (though it may log errors).
    """
    # Make maintain_global_connection() eventually exit
    global _global_awaitable_connection
    global _global_stopping

    _global_stopping.set_result(None)

    # Wait for maintain_global_connection() to exit
    try:
        connection = await _global_awaitable_connection  # or raise
        # If it returned, `maintain_global_connection()` will close it
        await connection.closed  # or raise
    except Exception as err:
        logger.exception("RabbitMQ error during close: %s", str(err))

    # Hack: make sure `maintain_global_connection()` finishes before we do
    await asyncio.sleep(0)

    assert _global_awaitable_connection == None
    assert _global_stopping == None
