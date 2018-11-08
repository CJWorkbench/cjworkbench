import asyncio
import logging
import threading
import types
import aio_pika
from django.conf import settings
import msgpack

# Support multiple event loops. This only makes sense during unit tests:
# async_to_sync() creates and destroys an event loop with each invocation.
_connect_lock = threading.Lock()  # only connect in one event loop at a time
_loop_to_connection = {}  # loop => (connection, channel)


logger = logging.getLogger(__name__)


class Connection:
    def __init__(self, connection, channel):
        self.connection = connection
        self.channel = channel
        self.lock = asyncio.Lock()

    async def close(self) -> None:
        await self.channel.close()
        await self.connection.close()

    async def queue_render(self, workflow_id: int, delta_id: int) -> None:
        async with self.lock:
            await self.channel.default_exchange.publish(
                aio_pika.Message(msgpack.packb({
                    'workflow_id': workflow_id,
                    'delta_id': delta_id,
                })),
                routing_key='render'
            )

    async def queue_fetch(self, wf_module_id: int) -> None:
        async with self.lock:
            await self.channel.default_exchange.publish(
                aio_pika.Message(msgpack.packb({
                    'wf_module_id': wf_module_id,
                })),
                routing_key='fetch'
            )

    async def queue_handle_upload_DELETEME(self, wf_module_id: int,
                                           uploaded_file_id: int) -> None:
        """
        DELETEME: see https://www.pivotaltracker.com/story/show/161509317
        """
        async with self.lock:
            await self.channel.default_exchange.publish(
                aio_pika.Message(msgpack.packb({
                    'wf_module_id': wf_module_id,
                    'uploaded_file_id': uploaded_file_id,
                })),
                routing_key='DELETEME-upload'
            )


async def get_connection(loop=None):
    if not loop:
        loop = asyncio.get_event_loop()

    global _loop_to_connection
    try:
        return _loop_to_connection[loop]
    except KeyError:
        global _connect_lock

        with _connect_lock:
            host = settings.RABBITMQ_HOST
            logger.info('Connecting to %s', host)
            connection = await aio_pika.connect_robust(url=host,
                                                       connection_attempts=100)
            channel = await connection.channel()
            await channel.declare_queue('render', durable=True)
            await channel.declare_queue('fetch', durable=True)
            await channel.declare_queue('DELETEME-upload', durable=True)

            def _wrap_event_loop(self, *args, **kwargs):  # self = loop
                global _loop_to_connection

                # If the event loop was closed, there's nothing we can do
                if not self.is_closed():
                    try:
                        conn = _loop_to_connection[loop]
                        del _loop_to_connection[self]
                        self.run_until_complete(conn.close())
                    except KeyError:
                        pass

                # Restore and call the original close()
                self.close = original_impl
                return self.close(*args, **kwargs)

            original_impl = loop.close
            loop.close = types.MethodType(_wrap_event_loop, loop)

            _loop_to_connection[loop] = Connection(connection, channel)
            return _loop_to_connection[loop]


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
    Write is_busy=True and queue handle-upload in RabbitMQ.

    DELETEME delete this entire queue. See
    https://www.pivotaltracker.com/story/show/161509317 for the path forward.
    """
    connection = await get_connection()
    await uploaded_file.wf_module.set_busy()  # TODO make this more obvious
    await connection.queue_handle_upload_DELETEME(uploaded_file.wf_module_id,
                                                  uploaded_file.id)
