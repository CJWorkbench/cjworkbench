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
import pickle
from typing import Callable, Dict

import msgpack
from aiormq.exceptions import DeliveryError

from .. import clientside
from .connection import RetryingConnection, get_connection


logger = logging.getLogger(__name__)


Render = "render"
Fetch = "fetch"


def _workflow_group_name(workflow_id: int) -> str:
    """Build a channel_layer group name, given a workflow ID.

    Messages sent to this group will be sent to all clients connected to
    this workflow.
    """
    return f"workflow-{str(workflow_id)}"


def acking_callback(fn):
    """
    Decorate a callback to ack when finished or crash on error.

    Usage:

        @rabbitmq.acking_callback
        async def handle_render_message(message: Dict[str, Any]):
            pass

        # Begin consuming
        await connection.consume(rabbitmq.Render, handle_render_message, 3)
    """

    @functools.wraps(fn)
    async def inner(message):
        channel = message.channel
        delivery_tag = message.delivery.delivery_tag

        try:
            body = msgpack.unpackb(message.body)
            await fn(body)
            await channel.basic_ack(delivery_tag)
        except Exception as err:
            # [2021-02-11, adamhooper] The errors we see on production might
            # be different than in dev mode; so we'll always re-raise them.
            # The behavior we want: on production, _any_ error causes the
            # whole fetch to crash without acking. Not-acking means RabbitMQ
            # won't send us any more messages. So let's shut down, leading to
            # a restart of the whole process.
            #
            # In the case of `fn()` raising an exception, we _want_ that message
            # logged. Ditto when `channel.basic_ack()` fails.
            #
            # We don't want to log exceptions during graceful shutdown, though.
            logger.exception("Failed to consume a message; shutting down")
            try:
                await get_connection().close()
            finally:
                raise err

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
    await connection.publish("render", dict(workflow_id=workflow_id, delta_id=delta_id))


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
    await connection.publish("fetch", dict(workflow_id=workflow_id, step_id=step_id))


async def _queue_for_group(*, workflow_id: int, **kwargs) -> None:
    connection = await _get_connection_async()
    group_name = _workflow_group_name(workflow_id)
    data = dict(__asgi_group__=group_name, workflow_id=workflow_id, **kwargs)
    try:
        await connection.publish(
            group_name,
            data,
            # exchange="groups" magic string is defined here:
            # https://github.com/CJWorkbench/channels_rabbitmq#groups_exchange
            exchange="groups",
        )
    except DeliveryError:
        logger.warning(
            "Did not deliver to all queues on group %r: a queue is at capacity",
            group_name,
        )


async def send_update_to_workflow_clients(
    workflow_id: int, update: clientside.Update
) -> None:
    """
    Send a message *from* any async service *to* a Django Channels group.

    Django Channels will call Websockets consumers' `send_pickled_update()`
    method.

    Start and cache a RetryingConnection on the current event loop if there
    isn't one already. (`loop.close()` will be monkey-patched to disconnect.)

    This sends on a RabbitMQ topic exchange called "groups". (That magic
    string is described at
    https://github.com/CJWorkbench/channels_rabbitmq#groups_exchange.)
    RabbitMQ will deliver the message to each matching queue.

    If one of those queues is full, we may warn about a DeliveryError
    error. The message will still be delivered to other queues. (See
    https://www.rabbitmq.com/maxlength.html#overflow-behaviour.) Since
    "full queue" usually means "shaky HTTP connection" or "stalled web
    browser", the user probably won't notice that we drop the message.
    """
    pickled_update = pickle.dumps(update)
    await _queue_for_group(
        workflow_id=workflow_id,
        type="send_pickled_update",
        pickled_update=pickled_update,
    )


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

    Start and cache a RetryingConnection on the current event loop if there
    isn't one already. (`loop.close()` will be monkey-patched to disconnect.)

    This sends on a RabbitMQ topic exchange called "groups". (That magic
    string is described at
    https://github.com/CJWorkbench/channels_rabbitmq#groups_exchange.)
    RabbitMQ will deliver the message to each matching queue.

    If one of those queues is full, we may warn about a DeliveryError
    error. The message will still be delivered to other queues. (See
    https://www.rabbitmq.com/maxlength.html#overflow-behaviour.) Since
    "full queue" usually means "shaky HTTP connection" or "stalled web
    browser", the user probably won't notice that we drop the message.
    """
    await _queue_for_group(
        workflow_id=workflow_id, type="queue_render", delta_id=delta_id
    )
