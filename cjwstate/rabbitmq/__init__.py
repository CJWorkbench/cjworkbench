"""Django-agnostic RabbitMQ connection.

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
import logging
import pickle
from typing import Any, Dict

import carehare
import msgpack

from .. import clientside
from .connection import get_global_connection

logger = logging.getLogger(__name__)


Render = "render"
"""Name of queue that 'renderer' listens to."""

Fetch = "fetch"
"""Name of queue that 'fetcher' listens to."""

GroupsExchange = "groups"
"""Name of exchange upon which we publish user/workflow updates.

This magic string is described at
https://github.com/CJWorkbench/channels_rabbitmq#groups_exchange.
"""

Intercom = "intercom"
"""Name of queue that 'intercom-sink' listens to.

Intercom messages are fire-and-forget. We send them through a queue because our
RabbitMQ cluster is faster (and more reliable) than Intercom's API.
"""


def _workflow_group_name(workflow_id: int) -> str:
    """Build a channel_layer group name, given a workflow ID.

    Messages sent to this group will be sent to all clients connected to
    this workflow.
    """
    return f"workflow-{str(workflow_id)}"


async def queue_render(workflow_id: int, delta_id: int) -> None:
    """Queue render in RabbitMQ.

    Spurious renders are fine: these messages are tiny, and renderers ignore
    them gracefully.

    `maintain_global_connection()` must be running.

    Raise if our RabbitMQ connection is in turmoil. (Some other caller should
    shut down our process in that case.)
    """
    connection = await get_global_connection()
    await connection.publish(
        msgpack.packb(dict(workflow_id=workflow_id, delta_id=delta_id)),
        routing_key=Render,
    )


async def queue_fetch(workflow_id: int, step_id: int) -> None:
    """Queue fetch in RabbitMQ.

    The fetcher will set is_busy=False when fetch is complete. Spurious fetches
    may make the is_busy flag flicker, but if the user goes away we're
    guaranteed that the fetcher will have the last word and is_busy will be
    False.

    The caller should consider sending is_busy=True when calling this. (TODO
    solve race: can't set is_busy _before_ queue_fetch() or we could leak the
    message; can't set it _after_ or the fetcher could finish first.)

    `maintain_global_connection()` must be running.

    Raise if our RabbitMQ connection is in turmoil. (Some other caller should
    shut down our process in that case.)
    """
    connection = await get_global_connection()
    await connection.publish(
        msgpack.packb(dict(workflow_id=workflow_id, step_id=step_id)),
        routing_key=Fetch,
    )


async def queue_intercom_message(
    *, http_method: str, http_path: str, data: Dict[str, Any]
) -> None:
    """Queue a message for sending to Intercom.

    `maintain_global_connection()` must be running.

    Raise if our RabbitMQ connection is in turmoil. (Some other caller should
    shut down our process in that case.)
    """
    connection = await get_global_connection()
    await connection.publish(
        msgpack.packb(dict(method=http_method, path=http_path, data=data)),
        routing_key=Intercom,
    )


async def _queue_for_group(*, workflow_id: int, **kwargs) -> None:
    connection = await get_global_connection()
    group_name = _workflow_group_name(workflow_id)
    data = dict(__asgi_group__=group_name, workflow_id=workflow_id, **kwargs)
    try:
        await connection.publish(
            msgpack.packb(data),
            exchange_name=GroupsExchange,
            routing_key=group_name,
        )
    except carehare.ServerSentNack:
        logger.warning(
            "Did not deliver to all queues on group %r: a queue is at capacity",
            (group_name,),
        )


async def send_update_to_workflow_clients(
    workflow_id: int, update: clientside.Update
) -> None:
    """
    Send a message *from* any async service *to* a Django Channels group.

    `maintain_global_connection()` must be running.

    Django Channels will call Websockets consumers' `send_pickled_update()`
    method.

    If one of those queues is full, we may warn about a DeliveryError
    error. The message will still be delivered to other queues. (See
    https://www.rabbitmq.com/maxlength.html#overflow-behaviour.) Since
    "full queue" usually means "shaky HTTP connection" or "stalled web
    browser", the user probably won't notice that we drop the message.

    Raise if our RabbitMQ connection is in turmoil. (Some other caller should
    shut down our process in that case.)
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
    """Tell workflow consumers to call `queue_render(workflow_id, delta_id)`.

    In other words: "queue a render, but only if somebody has this workflow
    open in a web browser."

    Django Channels will call Websockets consumers' `queue_render()` method.
    Each consumer will (presumably) call `cjwstate.rabbitmq.queue_render()`.
    (Renderers will ignore spurious calls. If there are no consumers,
    queue_render() won't be called -- saving us a render.)

    `maintain_global_connection()` must be running.

    If one of those queues is full, we may warn about a DeliveryError
    error. The message will still be delivered to other queues. (See
    https://www.rabbitmq.com/maxlength.html#overflow-behaviour.) Since
    "full queue" usually means "shaky HTTP connection" or "stalled web
    browser", the user probably won't notice that we drop the message.

    Raise if our RabbitMQ connection is in turmoil. (Some other caller should
    shut down our process in that case.)
    """
    await _queue_for_group(
        workflow_id=workflow_id, type="queue_render", delta_id=delta_id
    )
