import asyncio
import logging
import math
import os
import time
import warnings

from cjworkbench.pg_render_locker import PgRenderLocker
from cjworkbench.util import benchmark


logger = logging.getLogger(__name__)


FetchInterval = 60  # seconds


async def queue_fetches_forever():
    from .autoupdate import queue_fetches  # AFTER django.setup() init

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


def exit_on_exception(loop, context):
    logger.error(
        "Exiting because of unhandled error: %s\nContext: %r",
        context["message"],
        context,
        exc_info=context.get("exception"),
    )
    os._exit(1)


async def main():
    """
    Run maintenance tasks in the background.

    This should run forever, as a singleton daemon.
    """
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(exit_on_exception)
    await queue_fetches_forever()


if __name__ == "__main__":
    import django

    django.setup()
    asyncio.run(main())
