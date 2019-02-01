import asyncio
from functools import partial
import logging
import os
import aio_pika
from server import rabbitmq
from .pg_locker import PgLocker
from .fetch import handle_fetch
from .upload_DELETEME import handle_upload_DELETEME
from .render import handle_render, send_render


logger = logging.getLogger(__name__)


# Resource limits per process
#
# Workers do different tasks. (Arguably, we could make them separate
# microservices; but Django-laden processes cost ~100MB so let's use fewer.)
# These tasks can run concurrently, if they're async.

# NRenderers: number of renders to perform simultaneously. This should be 1 per
# CPU, because rendering is CPU-bound. (It uses a fair amount of RAM, too.)
#
# Default is 1: we expect to run on a 2-CPU machine, so 1 CPU for render and 1
# for cron-render.
NRenderers = int(os.getenv('CJW_WORKER_N_RENDERERS', 1))

# NFetchers: number of fetches to perform simultaneously. Fetching is
# often I/O-heavy, and some of our dependencies use blocking calls, so we
# allocate a thread per fetcher. Larger files may use lots of RAM.
#
# Default is 3: these mostly involve waiting for remote servers, though there's
# also some RAM required for bigger tables.
NFetchers = int(os.getenv('CJW_WORKER_N_FETCHERS', 3))

# NUploaders: number of uploaded files to process at a time. TODO turn these
# into fetches - https://www.pivotaltracker.com/story/show/161509317. We handle
# the occasional 1GB+ file, which will consume ~3GB of RAM, so let's keep this
# number at 1
#
# Default is 1: we don't expect many uploads.
NUploaders = int(os.getenv('CJW_WORKER_N_UPLOADERS', 1))


async def consume_queue(connection, queue_name, n_consumers, callback):
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=n_consumers)
    queue = await channel.declare_queue(queue_name, durable=True)
    await queue.consume(callback, no_ack=False)
    logger.info('Listening for %s requests', queue_name)


async def listen_for_renders(pg_locker: PgLocker,
                             connection: aio_pika.Connection,
                             n_renderers: int) -> None:
    """
    Run renders, forever.
    """
    render = partial(handle_render, pg_locker, send_render)
    await consume_queue(connection, 'render', n_renderers, render)


async def listen_for_fetches(connection: aio_pika.Connection,
                             n_fetchers: int) -> None:
    """
    Listen for fetches, forever.

    We'll accept NFetchers unacknowledged fetches.
    """
    await consume_queue(connection, 'fetch', n_fetchers, handle_fetch)


async def DELETEME_listen_for_uploads(connection: aio_pika.Connection,
                                      n_uploaders: int) -> None:
    """
    Listen for uploads, forever.

    DELETEME: uploaded files should be ParameterVals, and we should process
    them in render().
    """
    await consume_queue(connection, 'DELETEME-upload', n_uploaders,
                        handle_upload_DELETEME)


async def main_loop():
    """
    Run fetchers and renderers, forever.
    """
    connection = (await rabbitmq.get_connection()).connection
    async with PgLocker() as pg_locker:
        if NRenderers:
            await listen_for_renders(pg_locker, connection, NRenderers)
        if NFetchers:
            await listen_for_fetches(connection, NFetchers)
        if NUploaders:
            await DELETEME_listen_for_uploads(connection, NUploaders)

        # Run forever
        while True:
            await asyncio.sleep(99999)
