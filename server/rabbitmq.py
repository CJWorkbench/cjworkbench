import asyncio
from cjwstate import rabbitmq


async def get_connection_async():
    """
    Ensure rabbitmq is initialized.

    This is pretty janky.
    """
    ret = rabbitmq.get_connection()

    # Now, ret is returned but ret.connect() hasn't been called -- meaning we
    # can't call any other functions on it.
    #
    # Tell asyncio to start that `.connect()` (which has already been
    # scheduled)  _before_ doing anything else. sleep(0) does the trick.
    await asyncio.sleep(0)

    return ret


async def queue_render(workflow_id: int, delta_id: int):
    """
    Queue render in RabbitMQ.

    Spurious renders are fine: these messages are tiny, and renderers ignore
    them gracefully.
    """
    connection = await get_connection_async()
    await connection.queue_render(workflow_id, delta_id)


async def queue_fetch(workflow_id: int, wf_module_id: int):
    """
    Queue fetch in RabbitMQ.

    The fetcher will set is_busy=False when fetch is complete. Spurious fetches
    may make the is_busy flag flicker, but if the user goes away we're
    guaranteed that the fetcher will have the last word and is_busy will be
    False.

    Set is_busy=True when calling this. (TODO solve race: can't set is_busy
    _before_ queue_fetch() or we could leak the message; can't set it _after_
    or the fetcher could finish first.)
    """
    connection = await get_connection_async()
    await connection.queue_fetch(workflow_id, wf_module_id)
