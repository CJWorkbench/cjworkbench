import asyncio
import logging
import math
import time

from cjworkbench.pg_render_locker import PgRenderLocker
from cjworkbench.util import benchmark


logger = logging.getLogger(__name__)


FetchInterval = 60  # seconds


async def main():
    """Queue fetches for users' "automatic updates".

    Run this forever, as a singleton daemon.
    """
    from .autoupdate import queue_fetches  # AFTER django.setup()
    from cjwstate import rabbitmq
    from cjwstate.rabbitmq.connection import open_global_connection

    async with PgRenderLocker() as pg_render_locker, open_global_connection() as rabbitmq_connection:
        await rabbitmq_connection.exchange_declare(rabbitmq.GroupsExchange)
        await rabbitmq_connection.queue_declare(rabbitmq.Fetch)

        while not rabbitmq_connection.closed.done():
            t1 = time.time()

            await benchmark(logger, queue_fetches(pg_render_locker), "queue_fetches()")

            # Try to fetch at the beginning of each interval. Canonical example
            # is FetchInterval=60: queue all our fetches as soon as the minute
            # hand of the clock moves.

            next_t = (math.floor(t1 / FetchInterval) + 1) * FetchInterval
            delay = max(0, next_t - time.time())
            # Sleep ... or die, if RabbitMQ dies.
            await asyncio.wait({rabbitmq_connection.closed}, timeout=delay)  # raise

        await rabbitmq_connection.closed  # raise on failure
        # Now, raise on _success_! We should never get here
        raise RuntimeError(
            "RabbitMQ closed successfully. That's strange because cron never closes it."
        )


if __name__ == "__main__":
    import django

    django.setup()
    asyncio.run(main())
