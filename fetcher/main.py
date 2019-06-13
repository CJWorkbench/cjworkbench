import os
from cjworkbench import rabbitmq
from .fetch import handle_fetch


# NFetchers: number of fetches to perform simultaneously. Fetching is
# often I/O-heavy, and some of our dependencies use blocking calls, so we
# allocate a thread per fetcher. Larger files may use lots of RAM.
#
# Default is 3: these mostly involve waiting for remote servers, though there's
# also some RAM required for bigger tables.
NFetchers = int(os.getenv('CJW_N_FETCHERS', 3))


async def main_loop():
    """
    Fetch, forever
    """
    connection = rabbitmq.get_connection()
    connection.declare_queue_consume(
        rabbitmq.Fetch,
        NFetchers,
        rabbitmq.acking_callback(handle_fetch)
    )
    # Run forever
    await connection._closed_event.wait()
