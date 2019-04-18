import asyncio
import logging
import os
from typing import Any, Awaitable, Callable, Dict
from channels.db import database_sync_to_async
from django.db import DatabaseError, InterfaceError
from server.models import Workflow
from .pg_locker import PgLocker, WorkflowAlreadyLocked
from .util import benchmark
from . import execute


logger = logging.getLogger(__name__)


# DupRenderWait: number of seconds to wait before queueing a re-render request.
# When a service requests a render of an already-rendering workflow, the
# running render will fail fast and a new render should begin. If we receive
# the request for a new render before the prior render failed fast, we'll wait
# a bit before rescheduling so we don't re-queue the render ten times per
# millisecond.
#
# If this is too low, we'll use lots of network traffic and CPU re-queueing a
# render over and over, if its Workflow is the only one in the queue. If it's
# too high, Workbench will idle instead of rendering (for half this duration,
# on average). Either way, the duplicate-render Workflow will be queued _last_
# so that other pending renders will occur before it.
DupRenderWait = 0.05  # s


@database_sync_to_async
def _lookup_workflow(workflow_id: int) -> Workflow:
    """Lookup workflow, or raise Workflow.DoesNotExist."""
    return Workflow.objects.get(id=workflow_id)


async def render_or_requeue(
    pg_locker: PgLocker,
    requeue: Callable[[int], Awaitable[None]],
    workflow_id: int,
    delta_id: int
) -> None:
    """
    Acquire an advisory lock and render, or re-queue task if the lock is held.

    If a render is requested on a Workflow that's already being rendered,
    there's no point in wasting CPU cycles starting from scratch. Wait for the
    first render to exit (which will happen at the next stale database-write)
    before trying again.
    """
    # Query for workflow before locking. We don't need a lock for this, and no
    # lock means we can dismiss spurious renders sooner, so they don't fill the
    # render queue.
    try:
        workflow = await _lookup_workflow(workflow_id)
    except Workflow.DoesNotExist:
        logger.info('Skipping render of deleted Workflow %d', workflow_id)
        return
    if workflow.last_delta_id != delta_id:
        logger.info('Ignoring stale render request %d for Workflow %d',
                    delta_id, workflow_id)
        return

    try:
        async with pg_locker.render_lock(workflow_id):
            # Most exceptions caught elsewhere.
            #
            # execute_workflow() will raise UnneededExecution if the workflow
            # changes while it's being rendered.
            #
            # We don't use `workflow.cooperative_lock()` because `execute` may
            # take ages (and it locks internally when it needs to).
            # `execute_workflow()` _anticipates_ that `workflow` data may be
            # stale.
            task = execute.execute_workflow(workflow, delta_id)
            await benchmark(logger, task, 'execute_workflow(%d, %d)',
                            workflow_id, delta_id)

    except WorkflowAlreadyLocked:
        logger.info('Workflow %d is being rendered elsewhere; rescheduling',
                    workflow_id)
        await requeue(DupRenderWait)

    except execute.UnneededExecution:
        logger.info('UnneededExecution in execute_workflow(%d)', workflow_id)
        # Don't requeue. Assume the process that modified the Workflow has also
        # scheduled a render. Indeed, that new render request may already have
        # hit WorkflowAlreadyLocked.
        return

    except DatabaseError:
        # Two possibilities:
        #
        # 1. There's a bug in worker.execute. This may leave the event
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


async def handle_render(pg_locker: PgLocker, message: Dict[str, Any],
                        requeue: Callable[[int], Awaitable[None]]) -> None:
        try:
            workflow_id = int(message['workflow_id'])
            delta_id = int(message['delta_id'])
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.info(
                ('Ignoring invalid render request. '
                 'Expected {workflow_id:int, delta_id:int}; got %r'),
                message
            )
            return

        try:
            task = render_or_requeue(pg_locker, requeue, workflow_id, delta_id)
            await benchmark(logger, task, 'render_or_requeue(%d, %d)',
                            workflow_id, delta_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception('Error during render')
