import asyncio
from functools import partial
import logging
import msgpack
import time
from typing import Awaitable, Callable
import aio_pika
import asyncpg
from async_generator import asynccontextmanager  # TODO python 3.7 native
from django.conf import settings
from django.utils import timezone
from server import execute
from server.models import UploadedFile, WfModule, Workflow
from server.updates import update_wf_module
from server.modules import uploadfile


logger = logging.getLogger(__name__)


# Resource limits per process
#
# Workers do different tasks. (Arguably, we could make them separate
# microservices; but Django-laden processes cost ~100MB so let's use fewer.)
# These tasks can run concurrently, if they're async.

# NRenderers: number of renders to perform simultaneously. This should be 1 per
# CPU, because rendering is CPU-bound. (It uses a fair amount of RAM, too.)
NRenderers = 1

# NFetchers: number of fetches to perform simultaneously. Fetching is
# often I/O-heavy, and some of our dependencies use blocking calls, so we
# allocate a thread per fetcher. Larger files may use lots of RAM.
NFetchers = 3

# NUploaders: number of uploaded files to process at a time. TODO turn these
# into fetches - https://www.pivotaltracker.com/story/show/161509317. We handle
# the occasional 1GB+ file, which will consume ~3GB of RAM, so let's keep this
# number at 1
NUploaders = 1

# DupRenderWait: number of seconds to wait before queueing a re-render request.
# When a service requests a render of an already-rendering workflow, the
# running render will fail fast and a new render should begin. If we receive
# the request for a new render before the prior render failed fast, we'll wait
# a bit before rescheduling so we don't re-queue the render ten times per
# millisecond.
#
# If this is too low, we'll use lots of network traffic and CPU re-queueing a
# render over and over, if its Workflow is the only one in the queue. If it's
# too high, Workbench will idle instead of rendering (for half this duration,
# on average). Either way, the duplicate-render Workflow will be queued _last_
# so that other pending renders will occur before it.
DupRenderWait = 0.05  # s


class WorkflowAlreadyLocked(Exception):
    pass


class PgLocker:
    """
    Distributed lock algorithm.

    Usage:

        async with PgLocker() as locker:
            try:
                async with locker.render_lock(workflow_id):
                    ...  # do stuff
            except WorkflowAlreadyLocked:
                ...  # do something else
    """

    def __init__(self):
        # Use a lock, so heartbeat queries won't interfere with advisory-lock
        # queries.
        self.pg_connection = None
        self.lock = asyncio.Lock()

    async def __aenter__(self) -> 'PgLocker':
        # pg_connection: asyncpg, not Django database, because we use its
        # transaction asynchronously. (Async is so much easier than threading....)
        pg_config = settings.DATABASES['default']
        pg_connection = await asyncpg.connect(
            host=pg_config['HOST'],
            user=pg_config['USER'],
            password=pg_config['PASSWORD'],
            database=pg_config['NAME'],
            port=pg_config['PORT'],
            timeout=pg_config['CONN_MAX_AGE'],
            command_timeout=pg_config['CONN_MAX_AGE']
        )

        self.pg_connection = pg_connection

        loop = asyncio.get_event_loop()
        interval = pg_config['CONN_MAX_AGE']
        self.heartbeat_task = loop.create_task(
            self.send_pg_heartbeats_forever(interval)
        )

        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        """Close connection (for unit tests)."""
        self.heartbeat_task.cancel()

        await self.pg_connection.close()

    async def send_pg_heartbeats_forever(self, interval: float) -> None:
        """
        Keep Postgres connection alive.
        """
        # Use connection_lock to make sure we don't send heartbeat queries at
        # the same time as we're sending BEGIN and COMMIT queries: we don't
        # want races.
        while True:
            await asyncio.sleep(interval)
            async with self.lock:
                await self.pg_connection.fetch(
                    "SELECT 'worker_heartbeat'",
                    timeout=interval
                )

    @asynccontextmanager
    async def render_lock(self, workflow_id: int) -> None:
        """
        Distributed lock manager, ensuring only one render per Workflow.

        This adds no correctness: only speed. We don't want two workers to
        render simultaneously because that's a waste of effort. Instead, they
        should both try to acquire the lock. If Worker B wants to render
        something Worker A is already rendering, then Worker A should postpone
        the render and pick some other task instead.

        Implementation: try to acquire a Postgres advisory lock from within a
        transaction and hold it for the duration of the render. Raise
        WorkflowAlreadyLocked if we cannot acquire the lock immediately.

        pg_advisory_lock() takes two int parameters (to make a 64-bit int). We'll
        give 0 as the first int (let's call 0 "category of lock") and the workflow
        ID as the second int. (Workflow IDs are 32-bit.) We use
        pg_try_advisory_xact_lock(0, workflow_id): `try` is non-blocking and `xact`
        means the lock will be released as soon as the transaction completes -- for
        instance, if a worker exits unexpectedly.
        """
        async with self.lock:
            async with self.pg_connection.transaction():
                success = await self.pg_connection.fetchval(
                    'SELECT pg_try_advisory_xact_lock(0, $1)',
                    workflow_id
                )
                if success:
                    yield
                else:
                    raise WorkflowAlreadyLocked


async def send_render(send_channel, send_lock, workflow_id: int) -> None:
    # We use asyncio.sleep() to avoid spinning. It would be nice to use a
    # RabbitMQ delayed exchange instead; that would involve a custom RabbitMQ
    # image, and as of 2018-10-30 the cost (new Docker image) seems to outweigh
    # the benefit (simpler client code).
    await asyncio.sleep(DupRenderWait)

    async with send_lock:
        await send_channel.default_exchange.publish(
            aio_pika.Message(msgpack.packb({'workflow_id': workflow_id})),
            routing_key='render'
        )


async def benchmark(task, message, *args):
    t1 = time.time()
    logger.info(f'Start {message}', *args)
    try:
        await task
    finally:
        t2 = time.time()
        logger.info(f'End {message} (%dms)', *args, 1000 * (t2 - t1))


async def render_or_reschedule(lock_render: Callable[[int], Awaitable[None]],
                               reschedule: Callable[[int], Awaitable[None]],
                               workflow_id: int) -> None:
    """
    Acquire an advisory lock and render, or re-queue task if the lock is held.

    If a render is requested on a Workflow that's already being rendered,
    there's no point in wasting CPU cycles starting from scratch. Wait for the
    first render to exit (which will happen at the next stale database-write)
    before trying again.
    """
    try:
        async with lock_render(workflow_id):
            workflow = Workflow.objects.get(id=workflow_id)

            # Most exceptions caught elsewhere.
            #
            # execute_workflow() will raise UnneededExecution if the workflow
            # changes while it's being rendered.
            task = execute.execute_workflow(workflow)
            await benchmark(task, 'execute_workflow(%d)', workflow_id)

    except WorkflowAlreadyLocked:
        logger.info('Workflow %d is being rendered elsewhere; rescheduling',
                    workflow_id)
        await reschedule(workflow_id)

    except Workflow.DoesNotExist:
        logger.info('Skipping render of deleted Workflow %d', workflow_id)
        return

    except execute.UnneededExecution:
        logger.info('UnneededExecution in execute_workflow(%d)',
                    workflow_id)
        # Don't reschedule. Assume the process that modified the
        # Workflow has also scheduled a render. Indeed, that new render
        # request may already have hit WorkflowAlreadyLocked.
        return


async def fetch(*, wf_module_id: int) -> None:
    try:
        wf_module = WfModule.objects.get(id=wf_module_id)
    except WfModule.DoesNotExist:
        logger.info('Skipping fetch of deleted WfModule %d', wf_module_id)
        return

    now = timezone.now()
    # exceptions caught elsewhere
    task = update_wf_module(wf_module, now)
    await benchmark(task, 'update_wf_module(%d)', wf_module_id)


async def upload_DELETEME(*, wf_module_id: int, uploaded_file_id: int) -> None:
    """
    DELETEME: see https://www.pivotaltracker.com/story/show/161509317
    """
    try:
        wf_module = WfModule.objects.get(id=wf_module_id)
    except WfModule.DoesNotExist:
        logger.info('Skipping upload_DELETEME of deleted WfModule %d',
                    wf_module_id)
        return

    try:
        uploaded_file = UploadedFile.objects.get(id=uploaded_file_id)
    except WfModule.DoesNotExist:
        logger.info('Skipping upload_DELETEME of deleted UploadedFile %d',
                    uploaded_file_id)
        return

    # exceptions caught elsewhere
    task = uploadfile.upload_to_table(wf_module, uploaded_file)
    await benchmark(task, 'upload_to_table(%d, %d)', wf_module_id,
                    uploaded_file_id)


async def handle_render(lock_render: Callable[[int], Awaitable[None]],
                        reschedule: Callable[[int], Awaitable[None]],
                        message: aio_pika.IncomingMessage) -> None:
    with message.process():
        kwargs = msgpack.unpackb(message.body, raw=False)
        try:
            await render_or_reschedule(lock_render, reschedule, **kwargs)
        except:
            logger.exception('Error during render')


async def handle_fetch(message):
    with message.process():
        kwargs = msgpack.unpackb(message.body, raw=False)
        try:
            await fetch(**kwargs)
        except:
            logger.exception('Error during fetch')


async def handle_upload_DELETEME(message):
    """
    DELETEME: see https://www.pivotaltracker.com/story/show/161509317
    """
    with message.process():
        kwargs = msgpack.unpackb(message.body, raw=False)
        try:
            await upload_DELETEME(**kwargs)
        except:
            logger.exception('Error during fetch')


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
    lock_render = pg_locker.render_lock

    send_channel = await connection.channel(publisher_confirms=False)
    # Use a lock, so we don't send twice simultaneously over the same channel.
    # (We delay sends by DupRenderWait seconds and run them in the background:
    # two might be invoked concurrently.)
    send_lock = asyncio.Lock()
    reschedule_render = partial(send_render, send_channel, send_lock)

    render = partial(handle_render, lock_render, reschedule_render)
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
    Run one fetcher and one renderer, forever.
    """
    host = settings.RABBITMQ_HOST

    logger.info('Connecting to %s', host)
    connection = await aio_pika.connect_robust(url=host,
                                               connection_attempts=100)
    async with PgLocker() as pg_locker:
        await listen_for_renders(pg_locker, connection, NRenderers)
        await listen_for_fetches(connection, NFetchers)
        await DELETEME_listen_for_uploads(connection, NUploaders)

        # Run forever
        while True:
            await asyncio.sleep(1)
