"""
Django-agnostic RabbitMQ connection.

Workbench services actually use two RabbitMQ connections:

1. A connection for Django Channels, for Websockets messages. (Only the web
   server connects to RabbitMQ this way.)
2. This `cjwstate.rabbitmq` connection, for work queues.

Messages sent over Channels are per-HTTP-connection. Messages sent over *this*
connection are per-workflow.

The tiny bit of overlap: when renderer/fetcher want to send workflow updates
to all HTTP connections listening on a workflow, they _send_ using
`cjwstate.rabbitmq` ... and then the web server _receives_ those messages over
its Django Channels channel layer.
"""
import asyncio
import functools
import logging
from typing import Callable, Dict
import msgpack
from .. import clientside
from .connection import RetryingConnection, get_connection


logger = logging.getLogger(__name__)


Render = "render"
Fetch = "fetch"


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


def manual_acking_callback(fn):
    """
    Decode `message` and supply a no-arg `ack()` function to a callback.

    Usage:

        @rabbitmq.manual_acking_callback
        async def handle_render_message(message: Dict[str, Any],
                                        ack: Callable[[], Awaitable[None]]):
            # You _must_ ack. If you do not, a RuntimeError will be raised.
            await ack()

        # Begin consuming
        await connection.consume(rabbitmq.Render, handle_render_message, 3)
    """

    @functools.wraps(fn)
    async def inner(channel, body, envelope, properties):
        acked = False

        async def ack():
            nonlocal acked
            if acked:
                try:
                    raise RuntimeError
                except RuntimeError:
                    logger.exception("You called `ack()` twice")
            await channel.basic_client_ack(envelope.delivery_tag)
            acked = True

        try:
            message = msgpack.unpackb(body, raw=False)
            await fn(message, ack)
        finally:
            if not acked:
                try:
                    raise RuntimeError
                except RuntimeError:
                    logger.exception("You did not call ack()")
                await ack()

    return inner


async def _get_connection_async():
    """
    Ensure rabbitmq is initialized.

    This is pretty janky.
    """
    ret = get_connection()

    # Now, ret is returned but ret.connect() hasn't been called -- meaning we
    # can't call any other functions on it.
    #
    # Tell asyncio to start that `.connect()` (which has already been
    # scheduled)  _before_ doing anything else. sleep(0) does the trick.
    await asyncio.sleep(0)

    return ret


async def queue_render(workflow_id: int, delta_id: int) -> None:
    """
    Queue render in RabbitMQ.

    Spurious renders are fine: these messages are tiny, and renderers ignore
    them gracefully.

    Start and cache a RetryingConnection on the current event loop if there
    isn't one already. (`loop.close()` will be monkey-patched to disconnect.)
    """
    connection = await _get_connection_async()
    await connection.queue_render(workflow_id, delta_id)


async def queue_fetch(workflow_id: int, step_id: int) -> None:
    """
    Queue fetch in RabbitMQ.

    The fetcher will set is_busy=False when fetch is complete. Spurious fetches
    may make the is_busy flag flicker, but if the user goes away we're
    guaranteed that the fetcher will have the last word and is_busy will be
    False.

    The caller should consider sending is_busy=True when calling this. (TODO
    solve race: can't set is_busy _before_ queue_fetch() or we could leak the
    message; can't set it _after_ or the fetcher could finish first.)

    Start and cache a RetryingConnection on the current event loop if there
    isn't one already. (`loop.close()` will be monkey-patched to disconnect.)
    """
    connection = await _get_connection_async()
    await connection.queue_fetch(workflow_id, step_id)


async def send_update_to_workflow_clients(
    workflow_id: int, update: clientside.Update
) -> None:
    """
    Send a message *from* any async service *to* a Django Channels group.

    Django Channels will call Websockets consumers' `send_pickled_update()`
    method.

    Start and cache a RetryingConnection on the current event loop if there
    isn't one already. (`loop.close()` will be monkey-patched to disconnect.)
    """
    connection = await _get_connection_async()
    await connection.send_update_to_workflow_clients(workflow_id, update)


async def queue_render_if_consumers_are_listening(
    workflow_id: int, delta_id: int
) -> None:
    """
    Tell workflow consumers to call `queue_render(workflow_id, delta_id)`.

    In other words: "queue a render, but only if somebody has this workflow
    open in a web browser."

    Django Channels will call Websockets consumers' `queue_render()` method.
    Each consumer will (presumably) call `cjwstate.rabbitmq.queue_render()`.
    (Renderers will ignore spurious calls. And there are no consumers,
    queue_render() won't be called.)
    """
