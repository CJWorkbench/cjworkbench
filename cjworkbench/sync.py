import asyncio
from concurrent.futures import ThreadPoolExecutor
import contextvars
import functools
import sys
from channels.db import DatabaseSyncToAsync
from django.conf import settings


class WorkbenchDatabaseSyncToAsync(DatabaseSyncToAsync):
    """
    SyncToAsync on a special, database-only threadpool.

    Each thread has zero (on startup) or one (forever) database connection,
    stored in thread-local `django.db.connections[DEFAULT_DB_ALIAS]`.
    
    There is no way to close the threads' connections.

    This is how Channels' database_sync_to_async _should_ be implemented.
    We don't want ASGI_THREADS-many database connections because they thrash
    the database. Fewer connections means higher throughput. (We don't have any
    long-living SQL transactions; they'd change this calculus.)
    """

    executor = ThreadPoolExecutor(
        max_workers=settings.N_SYNC_DATABASE_CONNECTIONS,
        thread_name_prefix="workbench-database-sync-to-async-",
    )

    # override
    async def __call__(self, *args, **kwargs):
        # re-implementation of sync_to_async
        loop = asyncio.get_event_loop()
        context = contextvars.copy_context()
        child = functools.partial(self.func, *args, **kwargs)

        future = loop.run_in_executor(
            self.executor,
            functools.partial(
                self.thread_handler,
                loop,
                self.get_current_task(),
                sys.exc_info(),
                context.run,
                child,
            ),
        )
        return await asyncio.wait_for(future, timeout=None)


# The class is TitleCased, but we want to encourage use as a callable/decorator
database_sync_to_async = WorkbenchDatabaseSyncToAsync
