import asyncio
import logging
import math
import time
import warnings
from django.conf import settings
from cjworkbench.pg_render_locker import PgRenderLocker
from cjworkbench.util import benchmark
from .autoupdate import queue_fetches
from .sessions import delete_expired_sessions_and_workflows
from . import lessons


logger = logging.getLogger(__name__)


FetchInterval = 60  # seconds
ExpiryInterval = 300  # seconds
StaleUploadInterval = 7200  # seconds
StaleLessonAutoUpdateInterval = 3600  # seconds


async def queue_fetches_forever():
    async with PgRenderLocker() as pg_render_locker:
        while True:
            t1 = time.time()

            await benchmark(logger, queue_fetches(pg_render_locker), "queue_fetches()")

            # Try to fetch at the beginning of each interval. Canonical example
            # is FetchInterval=60: queue all our fetches as soon as the minute
            # hand of the clock moves.

            next_t = (math.floor(t1 / FetchInterval) + 1) * FetchInterval
            delay = max(0, next_t - time.time())
            await asyncio.sleep(delay)


async def delete_expired_sessions_and_workflows_forever():
    if settings.SESSION_ENGINE != "django.contrib.sessions.backends.db":
        warnings.warn(
            "WARNING: not deleting anonymous workflows because we do not know "
            "which sessions are expired. Rewrite "
            "delete_expired_sessions_and_workflows() to fix this problem."
        )
        # Run forever
        while True:
            await asyncio.sleep(999999)

    while True:
        await benchmark(
            logger,
            delete_expired_sessions_and_workflows(),
            "delete_expired_sessions_and_workflows()",
        )
        await asyncio.sleep(ExpiryInterval)


async def disable_stale_lesson_auto_update_forever():
    while True:
        await benchmark(
            logger,
            lessons.disable_stale_auto_update(),
            "lessons.disable_stale_auto_update()",
        )
        await asyncio.sleep(StaleLessonAutoUpdateInterval)


async def main():
    """
    Run maintenance tasks in the background.

    This should run forever, as a singleton daemon.
    """
    await asyncio.wait(
        {
            queue_fetches_forever(),
            delete_expired_sessions_and_workflows_forever(),
            disable_stale_lesson_auto_update_forever(),
        },
        return_when=asyncio.FIRST_EXCEPTION,
    )
