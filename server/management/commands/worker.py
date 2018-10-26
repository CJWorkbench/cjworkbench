import asyncio
import logging
import msgpack
import time
import aio_pika
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone, autoreload
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


async def benchmark(task, message, *args):
    t1 = time.time()
    logger.info(f'Start {message}', *args)
    try:
        await task
    finally:
        t2 = time.time()
        logger.info(f'End {message} (%dms)', *args, 1000 * (t2 - t1))


async def render(*, workflow_id: int) -> None:
    try:
        workflow = Workflow.objects.get(id=workflow_id)
    except Workflow.DoesNotExist:
        logger.info('Skipping render of deleted Workflow %d', workflow_id)
        return

    try:
        # Most exceptions caught elsewhere
        #
        # TODO prevent two worker processes from rendering the same workflow at
        # the same time. A second render should _cancel_ the first and then
        # restart from the top.
        task = execute.execute_workflow(workflow)
        await benchmark(task, 'execute_workflow(%d)', workflow_id)
    except execute.UnneededExecution:
        logger.info('UnneededExecution in execute_workflow(%d)', workflow_id)


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


async def handle_render(message):
    with message.process():
        kwargs = msgpack.unpackb(message.body, raw=False)
        try:
            await render(**kwargs)
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


async def main_loop():
    """
    Run one fetcher and one renderer, forever.
    """
    host = settings.RABBITMQ_HOST

    logger.info('Connecting to %s', host)

    connection = await aio_pika.connect_robust(url=host,
                                               connection_attempts=100)

    render_channel = await connection.channel()
    await render_channel.set_qos(prefetch_count=NRenderers)
    render_queue = await render_channel.declare_queue('render', durable=True)
    await render_queue.consume(handle_render, no_ack=False)
    logger.info('Listening for render requests')

    fetch_channel = await connection.channel()
    await fetch_channel.set_qos(prefetch_count=NFetchers)
    fetch_queue = await fetch_channel.declare_queue('fetch', durable=True)
    await fetch_queue.consume(handle_fetch, no_ack=False)
    logger.info('Listening for fetch requests')

    upload_DELETEME_channel = await connection.channel()
    await upload_DELETEME_channel.set_qos(prefetch_count=NUploaders)
    upload_DELETEME_queue = await (
        upload_DELETEME_channel.declare_queue('DELETEME-upload', durable=True)
    )
    await upload_DELETEME_queue.consume(handle_upload_DELETEME, no_ack=False)
    logger.info('Listening for upload_DELETEME requests')


def main():
    loop = asyncio.new_event_loop()
    loop.create_task(main_loop())
    loop.run_forever()
    loop.close()


class Command(BaseCommand):
    help = 'Continually delete expired anonymous workflows and fetch wfmodules'

    def handle(self, *args, **options):
        autoreload.main(main)
