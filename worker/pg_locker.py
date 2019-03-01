import asyncio
import asyncpg
from contextlib import asynccontextmanager
from django.conf import settings


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

    This client is re-entrant: it can lock multiple workflows at once.
    Double-locking a workflow will always raise WorkflowAlreadyLocked.
    """

    def __init__(self):
        self.pg_connection = None
        self.local_held_locks = set()

    async def __aenter__(self) -> 'PgLocker':
        # pg_connection: asyncpg, not Django database, because we use its
        # transaction asynchronously. (Async is so much easier than threading.)
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
            await self.pg_connection.fetch(
                "SELECT 'worker_heartbeat'",
                timeout=interval
            )

    @asynccontextmanager
    async def _local_lock(self, workflow_id: int) -> None:
        """
        Local lock manager, ensuring only one render per Workflow.

        pg_try_advisory_lock() docs say "Multiple lock requests stack" (on a
        single connection). For us, that means multiple local callers can lock
        the same workflow. ("local" here means, "on this connection".)

        The solution: wrap Postgres locks with a local locking system.
        """
        if workflow_id in self.local_held_locks:
            raise WorkflowAlreadyLocked

        self.local_held_locks.add(workflow_id)

        try:
            yield
        finally:
            self.local_held_locks.remove(workflow_id)

    @asynccontextmanager
    async def render_lock(self, workflow_id: int) -> None:
        """
        Distributed lock manager, ensuring only one render per Workflow.

        This adds no correctness: only speed. We don't want two workers to
        render simultaneously because that's a waste of effort. Instead, they
        should both try to acquire the lock. If Worker B wants to render
        something Worker A is already rendering, then Worker A should postpone
        the render and pick some other task instead.

        Implementation: try to acquire a Postgres advisory lock and hold it
        during render. Raise WorkflowAlreadyLocked if we cannot acquire the
        lock immediately.

        pg_try_advisory_lock() takes two int parameters (to make a 64-bit int).
        Give 0 as the first int (let's call 0 "category of lock") and workflow
        ID as the second int. (Workflow IDs are 32-bit.) We use
        pg_try_advisory_xact_lock(0, workflow_id): `try` is non-blocking.
        Postgres will release the lock if the session ends (e.g., the worker
        disconnects).
        """
        # raises WorkflowAlreadyLocked
        async with self._local_lock(workflow_id):
            if not await self.pg_connection.fetchval(
                'SELECT pg_try_advisory_lock(0, $1)',
                workflow_id
            ):
                raise WorkflowAlreadyLocked

            try:
                yield
            finally:
                await self.pg_connection.fetchval(
                    'SELECT pg_advisory_unlock(0, $1)',
                    workflow_id
                )
