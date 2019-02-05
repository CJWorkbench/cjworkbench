import asyncio
from cjworkbench import rabbitmq


async def get_connection():
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

    Spurious renders are fine: these messages are tiny.
    """
    connection = await get_connection()
    await connection.queue_render(workflow_id, delta_id)


async def queue_fetch(wf_module):
    """
    Write is_busy=True and queue render in RabbitMQ.

    The worker will set is_busy=False when fetch is complete. Spurious fetches
    may make the is_busy flag flicker, but if the user goes away we're
    guaranteed that the worker will have the last word and is_busy will be
    False.
    """
    connection = await get_connection()
    await connection.queue_fetch(wf_module.id)


async def queue_handle_upload_DELETEME(uploaded_file):
    """
    Queue handle-upload in RabbitMQ.

    DELETEME delete this entire queue. See
    https://www.pivotaltracker.com/story/show/161509317 for the path forward.
    """
    connection = await get_connection()
    await connection.queue_handle_upload_DELETEME(uploaded_file.wf_module_id,
                                                  uploaded_file.id)
