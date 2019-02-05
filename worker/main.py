import asyncio
from functools import partial
import logging
import os
import aio_pika
from cjworkbench import rabbitmq
from .pg_locker import PgLocker
from .fetch import handle_fetch
from .upload_DELETEME import handle_upload_DELETEME
from .render import handle_render


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


async def main_loop():
    """
    Run fetchers and renderers, forever.
    """
    async with PgLocker() as pg_locker:
        @rabbitmq.acking_callback_with_requeue
        async def render_callback(*args, **kwargs):
            return await handle_render(pg_locker, *args, **kwargs)

        connection = rabbitmq.get_connection()

        connection.declare_queue_consume(
            rabbitmq.Render,
            NRenderers,
            render_callback
        )
        connection.declare_queue_consume(
            rabbitmq.Fetch,
            NFetchers,
            rabbitmq.acking_callback(handle_fetch)
        )
        connection.declare_queue_consume(
            rabbitmq.DeletemeUpload,
            NUploaders,
            rabbitmq.acking_callback(handle_upload_DELETEME)
        )

        # Run forever
        while True:
            await asyncio.sleep(99999)
