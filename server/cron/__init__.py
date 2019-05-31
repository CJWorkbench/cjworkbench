import asyncio
import logging
import math
import time
import warnings
from django.conf import settings
from worker.pg_locker import PgLocker
from .autoupdate import queue_fetches
from .sessions import delete_expired_sessions_and_workflows
from .uploads import delete_stale_inprogress_file_uploads


logger = logging.getLogger(__name__)


FetchInterval = 60  # seconds
ExpiryInterval = 300  # seconds
StaleUploadInterval = 7200  # seconds


async def benchmark(task, message):
    t1 = time.time()
    logger.info(f'Start {message}')
    try:
        return await task
    finally:
        t2 = time.time()
        logger.info(f'End {message} (%dms)', 1000 * (t2 - t1))


async def queue_fetches_forever():
    async with PgLocker() as pg_locker:
        while True:
            t1 = time.time()

            await benchmark(queue_fetches(pg_locker), 'queue_fetches()')

            # Try to fetch at the beginning of each interval. Canonical example
            # is FetchInterval=60: queue all our fetches as soon as the minute
            # hand of the clock moves.

            next_t = (math.floor(t1 / FetchInterval) + 1) * FetchInterval
            delay = max(0, next_t - time.time())
            await asyncio.sleep(delay)


async def delete_expired_sessions_and_workflows_forever():
    if settings.SESSION_ENGINE != 'django.contrib.sessions.backends.db':
        warnings.warn(
            'WARNING: not deleting anonymous workflows because we do not know '
            'which sessions are expired. Rewrite '
            'delete_expired_sessions_and_workflows() to fix this problem.'
        )
        # Run forever
        while True:
            await asyncio.sleep(999999)

    while True:
        try:
            await benchmark(delete_expired_sessions_and_workflows(),
                            'delete_expired_sessions_and_workflows()')
        except:
            logger.exception('Error deleting expired sessions and workflows')

        await asyncio.sleep(ExpiryInterval)


async def delete_stale_inprogress_file_uploads_forever():
    while True:
        try:
            await benchmark(delete_stale_inprogress_file_uploads(),
                            'delete_stale_inprogress_file_uploads()')
        except:
            logger.exception('Error deleting stale inprogress uploads')

        await asyncio.sleep(StaleUploadInterval)


async def main():
    """
    Run maintenance tasks in the background.

    This should run forever, as a singleton daemon.
    """
    await asyncio.wait({
        queue_fetches_forever(),
        delete_expired_sessions_and_workflows_forever(),
        delete_stale_inprogress_file_uploads_forever(),
    }, return_when=asyncio.FIRST_EXCEPTION)
