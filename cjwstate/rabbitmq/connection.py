import asyncio
import functools
import logging
import types
from typing import Any, Awaitable, Callable, Dict, NamedTuple, Optional, Tuple

import aiormq
import msgpack
from aiormq.exceptions import AMQPConnectionError
from django.conf import settings

from .. import clientside


_loop_to_connection = {}
logger = logging.getLogger(__name__)


class DeclaredQueueConsume(NamedTuple):
    name: str
    """RabbitMQ queue name."""

    callback: Callable[[Any], Awaitable[None]]
    """Function to run on every queue element."""


class RetryingConnection:
    """A connection that will retry connecting.

    Usage:

        connection = RetryingConnection(url, 10, 1.5)
        connection.declare_consume('render', 2, handle_render)
        connection.declare_consume('fetch', 2, handle_fetch)

        await connection.connect_forever()
    """

    def __init__(self, url: str, attempts: int = 10, delay_s: float = 2.0):
        self.url = url
        self.attempts = attempts
        self.delay_s = delay_s
        self.is_closed = asyncio.Event()
        self._connected = asyncio.Event()
        self._declared_queues = []
        self._connection = None
        self._channel = None
        # _declared_exchanges: exchanges we have declared since our most recent
        # successful connect.
        #
        # When we send to an exchange we haven't sent to before, we declare it
        # first.
        self._declared_exchanges = None

    async def connect(self) -> None:
        """Ensure we are connected, setting `self._connection` to a value.

        Await this return value to test that the initial connection succeeds
        (within `attempts` retries).

        Sets self._connected when connected.
        """
        self._connected.clear()
        self._connection, self._channel = await self._connect()
        self._declared_exchanges = set()
        self._connected.set()

    async def connect_forever(self) -> None:
        """Connect and then reconnect forever, until `self.close()`.

        In the event that RabbitMQ closes the connection, we'll set
        self._connected to unfinished and retry connecting. Any current
        `publish` calls will raise `AmqpClosedConnection`; any _future_
        `publish` calls will await the reconnect.

        Intended calling convention is to run this once:

            connection = RetryingConnection(url, 10, 3.0)
            closed = asyncio.ensure_future(connection.connect_forever())
            ...
            # maybe somewhere, await connection.close()
            await closed  # raises error if connect fails 10 times in a row.
        """
        while not self.is_closed.is_set():
            await self.connect()  # raise if connect() fails over and over

            try:
                await self._connection.closing
            except AMQPConnectionError:
                # Once `.closing` completes, all futures have completed.
                # Loop, for the next connect() call.
                pass

    async def _connect(self) -> Tuple[aiormq.Connection, aiormq.Channel]:
        for attempt in range(self.attempts):
            try:
                return await self._attempt_connect()
            except AMQPConnectionError as err:
                if self.is_closed.is_set() or attempt >= self.attempts - 1:
                    raise
                else:
                    logger.info(
                        "Connection to RabbitMQ failed: %s; will retry in %fs",
                        str(err),
                        self.delay_s,
                    )
                    await asyncio.sleep(self.delay_s)

    async def _attempt_connect(self) -> Tuple[aiormq.Connection, aiormq.Channel]:
        """Set self._channel and self._connection, or raise.

        Raise AMQPConnectionError on error.
        """
        logger.info("Connecting to RabbitMQ at %s", self.url)
        connection = await aiormq.connect(self.url)
        channel = await connection.channel()

        logger.info("Negotiating with RabbitMQ")

        # _declare_ all queues right off the bat, before calling any callbacks.
        # (In theory, callbacks might depend on queues' existence).
        for queue in self._declared_queues:
            await channel.queue_declare(queue.name, durable=True)

        for queue in self._declared_queues:
            logger.info("Starting RabbitMQ consumer [%s]", queue.name)
            try:
                # RabbitMQ's 'basic_qos()' applies to "the next consumer", not the
                # actual channel. https://www.rabbitmq.com/consumer-prefetch.html
                #
                # leave prefetch_size at its default, 0: "no octet-size limit"
                await channel.basic_qos(prefetch_count=1)

                # call `callback` for every message. It must ack.
                await channel.basic_consume(queue.name, queue.callback)
            except AMQPConnectionError:
                logger.exception()
                raise

        logger.info("Connected to RabbitMQ")
        return connection, channel

    async def _ensure_connected(self):
        if not self._connected.is_set():
            await self._connected.wait()

    async def close(self) -> None:
        """Close the connection.

        Currently, closing a connection means waiting for it to open first.
        """
        self.is_closed.set()
        try:
            await self._ensure_connected()
            await self._connection.close()
        except AMQPConnectionError:
            pass

    async def wait_closed(self):
        """Wait for the connection to be closed.

        Currently, closing a connection means waiting for it to open first.
        """
        await self.is_closed.wait()
        await self._ensure_connected()
        try:
            await self._connection.closing
        except AMQPConnectionError:
            pass

    def declare_queue_consume(
        self, queue: str, callback: Callable[[Any], Awaitable[None]]
    ) -> None:
        """Declare a queue to be consumed after connect.

        Call this only during initialization. Do not call it after connect.

        (This is used on fetcher/renderer.)
        """
        self._declared_queues.append(DeclaredQueueConsume(queue, callback))

    async def publish(
        self, queue: str, message: Dict[str, Any], *, exchange: str = ""
    ) -> None:
        """Publish `message` onto `queue`, reconnecting if needed.

        (`queue` is really a "routing_key" in AMQP lingo. One can't publish
        directly to a queue. See
        https://www.rabbitmq.com/tutorials/amqp-concepts.html#exchange-default)
        """
        packed_message = msgpack.packb(message)

        await self._ensure_connected()
        if exchange and exchange not in self._declared_exchanges:
            await self._channel.exchange_declare(
                exchange=exchange, exchange_type="direct"
            )
            self._declared_exchanges.add(exchange)

        # Raise on error
        await self._channel.basic_publish(
            packed_message, exchange=exchange, routing_key=queue
        )


def get_connection(loop=None):
    """Create or lookup a singleton connection to RabbitMQ.

    Usage:

        def start():
            connection = get_connection()
            connection.declare_consume('render', 2, handle_render)
            connection.declare_consume('fetch', 2, handle_fetch)

    ... `connection.connect_forever()` will be scheduled to run on the event
    loop. Do not call `connection.declare_consume()` after connect.

    This function returns a different connection per event loop. This is used
    during unit tests, as each test starts up and destroys an event loop.
    """
    if not loop:
        loop = asyncio.get_event_loop()

    global _loop_to_connection

    connection = _loop_to_connection.get(loop)

    if not connection:
        # This is all sync, and it sets _loop_to_connection[loop]. No need for
        # locks.

        host = settings.RABBITMQ_HOST
        connection = RetryingConnection(host)
        monitor = asyncio.ensure_future(connection.connect_forever(), loop=loop)

        def _wrap_event_loop(self, *args, **kwargs):  # self = loop
            global _loop_to_connection

            # If the event loop was closed, there's nothing we can do
            if not self.is_closed():
                try:
                    del _loop_to_connection[self]
                except KeyError:
                    pass

                # disconnect from RabbitMQ...
                self.run_until_complete(connection.close())

                # ...and wait for the reconnector to exit.
                self.run_until_complete(monitor)

            # Restore and call the original close()
            self.close = original_impl
            return self.close(*args, **kwargs)

        original_impl = loop.close
        loop.close = types.MethodType(_wrap_event_loop, loop)

        _loop_to_connection[loop] = connection

    return connection
