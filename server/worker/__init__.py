import asyncio
from datetime import timedelta
from functools import partial
import logging
import msgpack
import os
import aio_pika
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from django.db import DatabaseError, InterfaceError
from django.utils import timezone
from server import rabbitmq, versions
from server.models import Params, LoadedModule, UploadedFile, WfModule
from server.modules import uploadfile
from .pg_locker import PgLocker
from .util import benchmark
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


MinFetchInterval = 5 * 60  # 5min


@database_sync_to_async
def _get_params(wf_module: WfModule) -> Params:
    return wf_module.get_params()


@database_sync_to_async
def _get_input_dataframe(wf_module_id: int):
    try:
        # Let's not worry about locks and races too much. All failures should
        # throw DoesNotExist, which is fine.
        wf_module = WfModule.objects.get(pk=wf_module_id)
        input_wf_module = wf_module.previous_in_stack()
    except WfModule.DoesNotExist:
        return None

    if not input_wf_module:
        return None

    crr = input_wf_module.get_cached_render_result(only_fresh=True)
    if not crr:
        return None
    else:
        return crr.result.dataframe


@database_sync_to_async
def _get_stored_dataframe(wf_module_id: int):
    try:
        wf_module = WfModule.objects.get(pk=wf_module_id)
    except WfModule.DoesNotExist:
        return None

    crr = wf_module.get_cached_render_result(only_fresh=True)
    if not crr:
        return None
    else:
        return crr.result.dataframe


@database_sync_to_async
def _get_workflow_owner(workflow_id: int):
    try:
        return User.objects.get(workflows__id=workflow_id)
    except User.DoesNotExist:
        return None


async def fetch_wf_module(wf_module, now):
    """Fetch `wf_module` and notify user of changes via email/websockets."""
    logger.debug('fetch_wf_module(%d, %d) at interval %d',
                 wf_module.workflow_id, wf_module.id,
                 wf_module.update_interval)
    try:
        params = await _get_params(wf_module)

        lm = await LoadedModule.for_module_version(wf_module.module_version)
        result = await lm.fetch(
            params,
            workflow_id=wf_module.workflow_id,
            get_input_dataframe=partial(_get_input_dataframe, wf_module.id),
            get_stored_dataframe=partial(_get_stored_dataframe, wf_module.id),
            get_workflow_owner=partial(_get_workflow_owner,
                                       wf_module.workflow_id),
        )

        await versions.save_result_if_changed(wf_module, result)
    except Exception as e:
        # Log exceptions but keep going
        logger.exception(f'Error fetching {wf_module}')

    update_next_update_time(wf_module, now)


def update_next_update_time(wf_module, now):
    """Schedule next update, skipping missed updates if any."""
    tick = timedelta(seconds=max(wf_module.update_interval, MinFetchInterval))
    wf_module.last_update_check = now

    if wf_module.next_update:
        while wf_module.next_update <= now:
            wf_module.next_update += tick
    wf_module.save(update_fields=['last_update_check', 'next_update'])


async def fetch(*, wf_module_id: int) -> None:
    try:
        wf_module = WfModule.objects.get(id=wf_module_id)
    except WfModule.DoesNotExist:
        logger.info('Skipping fetch of deleted WfModule %d', wf_module_id)
        return

    now = timezone.now()
    # most exceptions caught elsewhere
    try:
        task = fetch_wf_module(wf_module, now)
        await benchmark(logger, task, 'fetch_wf_module(%d)', wf_module_id)
    except DatabaseError:
        # Two possibilities:
        #
        # 1. There's a bug in module_dispatch_fetch. This may leave the event
        # loop's executor thread's database connection in an inconsistent
        # state. [2018-11-06 saw this on production.] The best way to clear
        # up the leaked, broken connection is to die. (Our parent process
        # should restart us, and RabbitMQ will give the job to someone
        # else.)
        #
        # 2. The database connection died (e.g., Postgres went away.) The
        # best way to clear up the leaked, broken connection is to die.
        # (Our parent process should restart us, and RabbitMQ will give the
        # job to someone else.)
        #
        # 3. There's some design flaw we haven't thought of, and we
        # shouldn't ever render this workflow. If this is the case, we're
        # doomed.
        #
        # If you're seeing this error that means there's a bug somewhere
        # _else_. If you're staring at a case-3 situation, please remember
        # that cases 1 and 2 are important, too.
        logger.exception('Fatal database error; exiting')
        os._exit(1)
    except InterfaceError:
        logger.exception('Fatal database error; exiting')
        os._exit(1)


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
