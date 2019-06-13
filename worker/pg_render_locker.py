from __future__ import annotations
import asyncio
import asyncpg
from collections import namedtuple
from contextlib import asynccontextmanager
from enum import Enum
import logging
from django.conf import settings


class WorkflowAlreadyLocked(Exception):
    pass


StallLockKey = 1
RenderLockKey = 2


_Lock = namedtuple('_Lock', ['stall_others'])


logger = logging.getLogger(__name__)


class PgRenderLocker:
    """
    Distributed lock algorithm.

    Usage:

        async with PgRenderLocker() as locker:
            try:
                # A. Lock the workflow for render.
                async with locker.render_lock(workflow_id) as lock:
                    # B. Do stuff. Other calls to render_lock() will raise
                    # WorkflowAlreadyLocked.
                    pass

                    await lock.stall_others()
                    # C. Do stuff. Other calls to render_lock() will stall
                    # until you exit this block.
                    if await _need_another_render(workflow_id):
                        await _requeue_render(workflow_id)
            except WorkflowAlreadyLocked:
                ...  # do something else

    This client is re-entrant. It can lock multiple workflows at once.
    Double-locking a workflow from within one client will behave exactly the
    way double-locking a workflow on two clients would behave.

    Another way of thinking of this lock is in "Phases". The problem we solve
    is: after rendering a workflow, we need to test whether the workflow is
    stale and queue another render if it is. (We don't want to re-render
    immediately, because that's unfair for other users.) So each workflow goes
    through these states, never skipping a step:

        unlocked --A--> rendering --B--> requeueing --C--> unlocked

    Each state transition is atomic -- and must be shared among all clients.

    * Transition A: unlocked -> rendering. If another worker is requeueing,
      stall until it's done. If another worker is rendering, raise
      WorkflowAlreadyLocked. Otherwise: after this returns, other workers will
      be prevented from making this transition.
    * Transition B: rendering -> requeueing. After this, other workers at step
      A will stall rather than raise WorkflowAlreadyLocked.
    * Transition C: requeueing -> unlocked. After this, other workers at step A
      will succed.

    Behind the scenes, this uses two Postgres advisory locks: the "stall" lock
    (advisory key1 '1') and the "render" lock (advisory key1 '2').

    * Transition A: lock "stall" lock (so we stall if in requeueing state);
      lock "render" lock; unlock "stall" lock.
    * Transition B: lock "stall" lock (we're entering requeueing state);
      unlock "render".
    * Transition C: unlock "stall" lock.

    Assumptions and invariants:
    * Once we queue a render on a Workflow, the queue will always have that
      Workflow queued (maybe unacked, maybe re-queued) until the Workflow is
      up-to-date.
    """

    def __init__(self):
        self.pg_connection = None
        self._pg_lock = asyncio.Lock()
        # Local lock state, ensuring only one render per Workflow.
        #
        # pg_advisory_lock() docs say "Multiple lock requests stack" (on a
        # single connection). For us, that means multiple local callers can
        # lock the same workflow. ("local" here means, "on this connection".)
        #
        # The solution: test and set local state (atomically) before querying
        # Postgres.
        self._local_stalls: Dict[int, asyncio.Event] = dict()
        self._local_renders: Set[int] = set()
        self._remote_stalls: Set[int] = set()  # for debugging
        self._remote_renders: Set[int] = set()  # for debugging

    async def __aenter__(self) -> PgRenderLocker:
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

    async def _pg_fetchval(self, sql, *args, **kwargs):
        async with self._pg_lock:
            return await self.pg_connection.fetchval(sql, *args, **kwargs)

    async def send_pg_heartbeats_forever(self, interval: float) -> None:
        """
        Keep Postgres connection alive.
        """
        while True:
            await asyncio.sleep(interval)
            await self._pg_fetchval("SELECT 'worker_heartbeat'",
                                    timeout=interval)
            # "heartbeat" log can help debug if the worker stalls, as
            # [2019-06-11] it did.
            logger.info(
                (
                    'heartbeat: local_stalls=%r, remote_stalls=%r, '
                    'local_renders=%r, remote_renders=%r'
                ) % (set(self._local_stalls.keys()), self._remote_stalls,
                     self._local_renders, self._remote_renders)
            )


    async def _release_remote_lock(self, key: int, workflow_id: int) -> None:
        await self._pg_fetchval('SELECT pg_advisory_unlock($1, $2)',
                                key, workflow_id)

    async def _acquire_local_stall_lock(self, workflow_id: int) -> None:
        # while-loop is important! If three _acquire_local_stall_lock() calls
        # contend, then two will return from .wait() but we only want one to
        # reach the next line.
        while workflow_id in self._local_stalls:
            await self._local_stalls[workflow_id].wait()
        self._local_stalls[workflow_id] = asyncio.Event()

    def _release_local_stall_lock(self, workflow_id: int) -> None:
        """
        Release the local stall, waking up other local-stall acquirers.
        """
        event = self._local_stalls.pop(workflow_id)
        event.set()

    async def _acquire_remote_stall_lock(self, workflow_id: int) -> None:
        await self._pg_fetchval('SELECT pg_advisory_lock($1, $2)',
                                StallLockKey, workflow_id)
        self._remote_stalls.add(workflow_id)

    async def _release_remote_stall_lock(self, workflow_id: int) -> None:
        self._remote_stalls.remove(workflow_id)
        await self._release_remote_lock(StallLockKey, workflow_id)

    def _acquire_local_render_lock(self, workflow_id: int) -> None:
        if workflow_id in self._local_renders:
            raise WorkflowAlreadyLocked
        self._local_renders.add(workflow_id)

    def _release_local_render_lock(self, workflow_id: int) -> None:
        self._local_renders.remove(workflow_id)

    async def _acquire_remote_render_lock(self, workflow_id: int) -> None:
        lock = await self._pg_fetchval('SELECT pg_try_advisory_lock($1, $2)',
                                       RenderLockKey, workflow_id)
        if not lock:
            raise WorkflowAlreadyLocked
        self._remote_renders.add(workflow_id)

    async def _release_remote_render_lock(self, workflow_id: int) -> None:
        self._remote_renders.remove(workflow_id)
        await self._release_remote_lock(RenderLockKey, workflow_id)

    @asynccontextmanager
    async def _local_stall_lock(self, workflow_id: int) -> None:
        await self._acquire_local_stall_lock(workflow_id)
        try:
            yield
        finally:
            self._release_local_stall_lock(workflow_id)

    @asynccontextmanager
    async def _remote_stall_lock(self, workflow_id: int) -> None:
        await self._acquire_remote_stall_lock(workflow_id)
        try:
            yield
        finally:
            await self._release_remote_stall_lock(workflow_id)

    async def _acquire_stall_lock(self, workflow_id: int) -> None:
        await self._acquire_local_stall_lock(workflow_id)
        await self._acquire_remote_stall_lock(workflow_id)

    async def _release_stall_lock(self, workflow_id: int) -> None:
        # Release in opposite order of acquiring
        await self._release_remote_stall_lock(workflow_id)
        self._release_local_stall_lock(workflow_id)

    @asynccontextmanager
    async def _stall_lock(self, workflow_id: int) -> None:
        async with self._local_stall_lock(workflow_id):
            async with self._remote_stall_lock(workflow_id):
                yield

    async def _acquire_render_lock(self, workflow_id: int) -> None:
        self._acquire_local_render_lock(workflow_id)
        try:
            await self._acquire_remote_render_lock(workflow_id)
        except:
            self._release_local_render_lock(workflow_id)
            raise

    async def _release_render_lock(self, workflow_id: int) -> None:
        # Release in opposite order of acquiring
        await self._release_remote_render_lock(workflow_id)
        self._release_local_render_lock(workflow_id)

    async def _transition_unlocked_to_rendering(self,
                                                workflow_id: int) -> None:
        """
        Stall if needed; raise WorkflowAlreadyLocked if needed; or do nothing.

        When this returns, the workflow is in the "rendering" state.
        """
        # Stall until we have the lock
        async with self._stall_lock(workflow_id):
            # Acquire the render lock, or raise WorkflowAlreadyLocked
            await self._acquire_render_lock(workflow_id)
        # Presto! Now other workers aren't stalled (we released _stall_lock);
        # so when they run this function they'll raise WorkflowAlreadyLocked

    async def _transition_rendering_to_requeueing(self,
                                                  workflow_id: int) -> None:
        """
        Stall every other worker for this workflow.

        When this returns, the workflow is in the "requeueing" state. Calls to
        _transition_unlocked_to_rendering() will stall (and then may succeed).
        None will raise WorkflowAlreadyLocked.
        """
        await self._acquire_stall_lock(workflow_id)
        await self._release_render_lock(workflow_id)
        # Presto! At this phase, no other worker is running code in
        # _transition_unlocked_to_rendering() -- they will all stall rather
        # than run that code.

    async def _transition_requeueing_to_unlocked(self,
                                                 workflow_id: int) -> None:
        """
        Unlock this workflow.

        This clears all remote and local state. Other callers will be unaware
        that we were ever in the "rendering" or "requeueing" states.
        """
        await self._release_stall_lock(workflow_id)
        # Presto! Now we hold no locks.

    @asynccontextmanager
    async def render_lock(self, workflow_id: int) -> None:
        """
        Distributed lock manager, ensuring only one render per Workflow.

        This adds no correctness: only speed. We don't want two workers to
        render simultaneously because that's a waste of effort. Instead, they
        should both try to acquire the lock. If Worker B wants to render
        something Worker A is already rendering, then Worker B should go away.
        (Worker A will reschedule the render when it's done, if needed.)
        """
        # Raises WorkflowAlreadyLocked
        await self._transition_unlocked_to_rendering(workflow_id)
        requeueing = False

        async def phase_b():
            await self._transition_rendering_to_requeueing(workflow_id)
            nonlocal requeueing
            requeueing = True
        
        lock = _Lock(phase_b)

        try:
            yield lock  # caller must call `await lock.stall_others()`
        finally:
            if not requeueing:
                # There's an off chance we can recover from this programmer
                # error without taking the site down. Make sure we get emailed
                # about it, at least.
                logger.error('You must `await lock.stall_others()`')
                await lock.stall_others()
            await self._transition_requeueing_to_unlocked(workflow_id)
