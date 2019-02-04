import asyncio
import functools
import logging
import types
from typing import Any, Callable, Dict
import aioamqp
from django.conf import settings
import msgpack


_loop_to_connection = {}
logger = logging.getLogger(__name__)


Render = 'render'
Fetch = 'fetch'
DeletemeUpload = 'DELETEME-upload'


class DeclaredQueueConsume:
    def __init__(self, name: str, prefetch_count: int, callback: Callable):
        self.name = name
        self.prefetch_count = prefetch_count
        self.callback = callback


def acking_callback(fn):
    """
    Decorate a callback to ack when finished or close the connection on error.

    Usage:

        @rabbitmq.acking_callback
        async def handle_render_message(message: Dict[str, Any]):
            pass

        # Begin consuming
        await connection.consume(rabbitmq.Render, handle_render_message, 3)
    """
    @functools.wraps(fn)
    async def inner(channel, body, envelope, properties):
        try:
            message = msgpack.unpackb(body, raw=False)
            await fn(message)
        finally:
            await channel.basic_client_ack(envelope.delivery_tag)

    return inner


def acking_callback_with_requeue(fn):
    """
    Decorate a callback to ack when finished or close the connection on error.

    Usage:

        @rabbitmq.acking_callback
        async def handle_render_message(message: Dict[str, Any],
                                        requeue: Callable):
            if we_are_ready:
                do_something()
            else:
                await requeue(0.1)  # will idle for 0.1s and then requeue

        # Begin consuming
        await connection.consume(rabbitmq.Render, handle_render_message, 3)
    """
    @functools.wraps(fn)
    async def inner(channel, body, envelope, properties):
        called_requeue = False
        async def requeue(delay: float):
            called_requeue = True
            # We use asyncio.sleep() to avoid spinning. During the sleep, we
            # are not rendering! It would be nice to use a RabbitMQ delayed
            # exchange instead; that would involve a custom RabbitMQ image, and
            # as of 2018-10-30 the cost (new Docker image) seems to outweigh
            # the benefit (less CPU wastage).
            await asyncio.sleep(delay)
            await channel.publish(body, '', routing_key=envelope.routing_key)

        try:
            message = msgpack.unpackb(body, raw=False)
            await fn(message, requeue)
        finally:
            await channel.basic_client_ack(envelope.delivery_tag)

    return inner


class RetryingConnection:
    """
    A connection that will retry connecting.

    Usage:

        connection = RetryingConnection(url, 10, 1.5)
        connection.declare_consume('render', 2, handle_render)
        connection.declare_consume('fetch', 2, handle_fetch)

        await connection.connect_forever()
    """

    def __init__(self, url: str, attempts: int, delay_s: float):
        self.url = url
        self.attempts = attempts
        self.delay_s = delay_s
        self.is_closed = False
        self._declared_queues = []
        self._closed_event = asyncio.Event()

    async def connect(self) -> None:
        """
        Ensure we are connected, setting `self._connection` to a value.

        Await this return value to test that the initial connection succeeds
        (within `attempts` retries).
        """
        # set self._connected to be an asyncio.Future, so we can await it
        # multiple times.
        self._connected = asyncio.ensure_future(self._connect())
        await self._connected  # raise if connection fails

    async def connect_forever(self) -> None:
        """
        Connect and then reconnect forever, until `self.close()`.

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
        while not self.is_closed:
            await self.connect()  # raise if connect() fails over and over

            # What happens on error? One of two things:
            #
            # 1. RabbitMQ closes self._channel. Why would it do this? Well,
            #    that's not for us to ask. The most common case is:
            # 2. RabbitMQ closes self._protocol. If it does, self._protocol
            #    will go and close self._channel.
            # 3. Network error. self._protocol.worker will return in that
            #    case.
            #
            # In cases 2 and 3, `self._protocol.run()` will raise
            # AmqpClosedConnection, close connections, and bail. In case 1, we
            # need to force the close ourselves.
            await self._channel.closed_event  # case 1, 2, 3

            # case 1 only: if the channel was closed and the connection wasn't,
            # wipe out the connection. (Otherwise, this is a no-op.)
            await self._protocol.close()

            # await self._protocol.worker so that every Future that's been
            # created gets awaited.
            await self._protocol.worker

    async def _connect(self) -> None:
        for attempt in range(self.attempts):
            try:
                return await self._attempt_connect()
            except ConnectionError as err:
                if self.is_closed or attempt >= self.attempts - 1:
                    raise
                else:
                    logger.info(
                        'Connection to RabbitMQ failed: %s; will retry in %fs',
                        str(err), self.delay_s
                    )
                    await asyncio.sleep(self.delay_s)
            except Exception:
                logger.exception('Unhandled exception from _attempt_connect()')
                raise

    async def _attempt_connect(self) -> None:
        """
        Set self._channel, self._transport and self._protocol, or raise.

        Known errors:

            ConnectionError: connection error
            TODO auth errors?
        """
        logger.info('Connecting to RabbitMQ at %s', self.url)
        self._transport, self._protocol = await aioamqp.from_url(self.url)
        self._channel = await self._protocol.channel()

        logger.info('Negotiating with RabbitMQ')

        # Set publisher confirms -- for requeue()
        await self._channel.confirm_select()

        # _declare_ all queues right off the bat, before calling any callbacks.
        # (In theory, callbacks might depend on queues' existence).
        for queue in self._declared_queues:
            await self._channel.queue_declare(queue.name, durable=True)

        logger.info('Starting RabbitMQ consumers')

        # Start consuming `self._declared_queues`
        for queue in self._declared_queues:
            if queue.prefetch_count == 0:
                # Don't actually _consume_ the queue: just declare it.
                continue

            # RabbitMQ's 'basic_qos()' applies to "the next consumer", not to the
            # actual channel. https://www.rabbitmq.com/consumer-prefetch.html
            #
            # leave prefetch_size at its default, 0: "no octet-size limit"
            await self._channel.basic_qos(prefetch_count=queue.prefetch_count)

            # call (and await) `callback` for every message.
            await self._channel.basic_consume(queue.callback,
                                              queue_name=queue.name)

        logger.info('Connected to RabbitMQ')

    async def close(self) -> None:
        """
        Close the connection.

        Currently, closing a connection means waiting for it to open first.
        """
        if self.is_closed:
            # Someone else called .close(). Return when that one finishes.
            await self._closed_event

        self.is_closed = True # speed up self.connect() if we're waiting for it

        await self._connected
        await self._protocol.close()
        await self._protocol.worker  # wait for connection to close entirely
        self._closed_event.set()  # we're finished closing.

    def declare_queue_consume(self, queue: str, prefetch_count: int,
                              callback: Callable) -> None:
        """
        Declare a queue to be consumed after connect.

        Call this only during initialization. Do not call it after connect.

        (This is used on the worker.)
        """
        self._declared_queues.append(
            DeclaredQueueConsume(queue, prefetch_count, callback)
        )

    def declare_queue(self, queue: str) -> None:
        """
        Declare a queue; do not consume from it.

        Call this only during initialization. Do not call it after connect.

        (This is used on the web server.)
        """
        self._declared_queues.append(DeclaredQueueConsume(queue, None, None))

    async def publish(self, queue: str, message: Dict[str, Any]) -> None:
        """
        Publish `message` onto `queue`, reconnecting if needed.
        """
        packed_message = msgpack.packb(message)

        await self._connected
        await self._channel.publish(packed_message, '', routing_key=queue)
        # On error, we'll set self.

    # Workbench-specific methods follow:

    async def queue_render(self, workflow_id: int, delta_id: int) -> None:
        await self.publish('render', {
            'workflow_id': workflow_id,
            'delta_id': delta_id,
        })

    async def queue_fetch(self, wf_module_id: int) -> None:
        await self.publish('fetch', {
            'wf_module_id': wf_module_id,
        })

    async def queue_handle_upload_DELETEME(self, wf_module_id: int,
                                           uploaded_file_id: int) -> None:
        """
        DELETEME: see https://www.pivotaltracker.com/story/show/161509317
        """
        await self.publish('DELETEME-upload', {
            'wf_module_id': wf_module_id,
            'uploaded_file_id': uploaded_file_id,
        })


def get_connection(loop=None):
    """
    Create or lookup a singleton connection to RabbitMQ.

    Usage:

        def start():
            connection = RetryingConnection(url, 10, 1.5)
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
        connection = RetryingConnection(host, 10, 2)
        monitor = asyncio.ensure_future(connection.connect_forever(),
                                        loop=loop)

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
