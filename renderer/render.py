import asyncio
import logging
from enum import Enum
from typing import Any, Dict, Optional

import carehare
from django.db import DatabaseError, InterfaceError

from cjwstate import rabbitmq
from cjwstate.models import Workflow
from cjworkbench.pg_render_locker import PgRenderLocker, WorkflowAlreadyLocked
from cjworkbench.sync import database_sync_to_async
from cjworkbench.util import benchmark
from . import execute


logger = logging.getLogger(__name__)


@database_sync_to_async
def _lookup_workflow(workflow_id: int) -> Workflow:
    """Lookup workflow, or raise Workflow.DoesNotExist."""
    return Workflow.objects.get(id=workflow_id)


class RenderResult(Enum):
    CHECK_TO_REQUEUE = 1
    MUST_REQUEUE = 2
    MUST_NOT_REQUEUE = 3


async def render_workflow_once(
    workflow: Workflow,
    delta_id: int,
    *,
    publish_dataset_spec: Optional[rabbitmq.PublishDatasetSpec],
):
    """Render a workflow, returning `RenderResult`.

    Considers all conceivable errors:

    * Treat UnneededExecution as success -- it's like a render, only faster!
      Always requeue, regardless of the workflow's delta: if the user does
      something and hits undo quickly, the delta ID is the same and yet we want
      to render again.
    * Raise asyncio.CancelledError if there was a cancellation. (This is always
      a bug -- we can't handle cancellation, and it isn't worth our effort.)
    * Re-raise basically any error we have vetted -- mostly DatabaseError. The
      process should exit (and log) when services fail, so it will restart and
      reconnect to them.
    * Catch _every other exception_ (!!!); email us. Return MUST_NOT_REQUEUE:
      we want to leave the workflow in an indeterminate state rather than cause
      this error over and over again.
    """
    # We don't use `workflow.cooperative_lock()` because `execute` may
    # take ages (and it locks internally when it needs to).
    # `execute_workflow()` _anticipates_ that `workflow` data may be
    # stale.
    try:
        task = execute.execute_workflow(workflow, delta_id)
        await benchmark(logger, task, "execute_workflow(%d, %d)", workflow.id, delta_id)
        return RenderResult.CHECK_TO_REQUEUE
    except execute.UnneededExecution:
        logger.info(
            "UnneededExecution in execute_workflow(%d, %d)", workflow.id, delta_id
        )
        return RenderResult.MUST_REQUEUE
    except asyncio.CancelledError:
        raise
    except (
        carehare.ChannelClosedByServer,
        carehare.ConnectionClosed,
        carehare.ServerSentNack,
        DatabaseError,
        InterfaceError,
    ):
        # These errors should cause a crash. A crash will restart this renderer
        # ... and the workflow will be picked up by another renderer.
        #
        # Why? Because...:
        #
        # * DatabaseError: network disconnect. Restart, reconnect.
        # * InterfaceError: postgres closed the connection. Restart, reconnect.
        # * carehare.ChannelClosedByServer: publish() from a Delta failed
        #       because e.g. missing exchange. Restart, reconnect -- we
        #       redeclare exchanges on startup.
        # * carehare.ServerSentNack: publish() from a Delta failed because a
        #       queue was full. Restart, reconnect -- we've never seen this,
        #       and hopefully if it ever happens it's transient.
        # * carehare.ConnectionClosed: publish() from a Delta failed because
        #       RabbitMQ is away. Restart, reconnect.
        raise
    except Exception:
        logger.exception("Error during render of workflow %d", workflow.id)
        return RenderResult.MUST_NOT_REQUEUE


async def render_workflow_and_maybe_requeue(
    pg_render_locker: PgRenderLocker,
    workflow_id: int,
    delta_id: int,
    *,
    publish_dataset_spec: Optional[rabbitmq.PublishDatasetSpec] = None,
) -> None:
    """Acquire an advisory lock and render, or re-queue if the lock is held.

    If a render is requested on a Workflow that's already being rendered,
    there's no point in wasting CPU cycles starting from scratch. Wait for the
    first render to exit (which will happen at the next stale database-write).
    It should then re-schedule a render.
    """
    # Query for workflow before locking. We don't need a lock for this, and no
    # lock means we can dismiss spurious renders sooner, so they don't fill the
    # render queue.
    try:
        workflow = await _lookup_workflow(workflow_id)
    except Workflow.DoesNotExist:
        logger.info("Skipping render of deleted Workflow %d", workflow_id)
        return

    try:
        async with pg_render_locker.render_lock(workflow_id) as lock:
            # any error leads to undefined behavior
            result = await render_workflow_once(
                workflow, delta_id, publish_dataset_spec=publish_dataset_spec
            )

            # requeue if needed
            await lock.stall_others()
            if result == RenderResult.MUST_REQUEUE:
                want_requeue = True
            elif result == RenderResult.MUST_NOT_REQUEUE:
                want_requeue = False
            else:
                try:
                    workflow = await _lookup_workflow(workflow_id)
                    if workflow.last_delta_id != delta_id:
                        logger.info(
                            "Requeueing render(workflow=%d, delta=%d)",
                            workflow_id,
                            workflow.last_delta_id,
                        )
                        want_requeue = True
                    else:
                        want_requeue = False
                except Workflow.DoesNotExist:
                    logger.info("Skipping requeue of deleted Workflow %d", workflow_id)
                    want_requeue = False
            if want_requeue:
                await rabbitmq.queue_render(workflow_id, workflow.last_delta_id)
                # This is why we used `lock.stall_others()`: after requeue,
                # another renderer may try to lock this workflow and we want
                # that lock to _succeed_ -- not raise WorkflowAlreadyLocked.
            # Only ack() _after_ requeue. That preserves our invariant: if we
            # schedule a render, there is always an un-acked render for that
            # workflow queued in RabbitMQ until the workflow is up-to-date. (At
            # this exact moment, there are briefly two un-acked renders.)
    except WorkflowAlreadyLocked:
        logger.info("Workflow %d is being rendered elsewhere; ignoring", workflow_id)


async def handle_render(
    message: Dict[str, Any],
    pg_render_locker: PgRenderLocker,
) -> None:
    try:
        workflow_id = int(message["workflow_id"])
        delta_id = int(message["delta_id"])
        publish_dataset_spec = (
            None
            if message.get("publish_dataset_spec") is None
            else rabbitmq.PublishDatasetSpec(**message["publish_dataset_spec"])
        )
    except (TypeError, ValueError, KeyError):
        # Message has invalid types. Ignore it.
        logger.info(
            (
                "Ignoring invalid render request. "
                "Expected {workflow_id:int, delta_id:int}; got %r"
            ),
            message,
        )
        return

    await render_workflow_and_maybe_requeue(
        pg_render_locker,
        workflow_id,
        delta_id,
        publish_dataset_spec=publish_dataset_spec,
    )
