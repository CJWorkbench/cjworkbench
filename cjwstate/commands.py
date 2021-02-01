from django.utils import timezone
from typing import Any, Dict, Optional, Tuple

from cjworkbench.sync import database_sync_to_async
from cjwstate import clientside, rabbitmq
from cjwstate.models import Delta, Step, Workflow
from cjwstate.models.commands import NAME_TO_COMMAND, SetStepDataVersion


async def websockets_notify(workflow_id: int, update: clientside.Update) -> None:
    """Notify Websockets clients of `update`; return immediately.

    This is an alias; its main purpose is for white-box unit testing.
    """
    await rabbitmq.send_update_to_workflow_clients(workflow_id, update)


async def queue_render(workflow_id: int, delta_id: int) -> None:
    """Tell renderer to render workflow; return immediately.

    This is an alias; its main purpose is for white-box unit testing.
    """
    await rabbitmq.queue_render(workflow_id, delta_id)


@database_sync_to_async
def _workflow_has_notifications(workflow_id: int) -> bool:
    """Detect whether a workflow sends email on changes."""
    return Step.live_in_workflow(workflow_id).filter(notifications=True).exists()


async def _maybe_queue_render(
    workflow_id: int, relevant_delta_id: int, delta: Delta
) -> None:
    """Tell renderer to render workflow; return immediately.

    `delta` is used to check for SetStepDataVersion, which gets special
    logic. But to be clear: the `delta` in question might have been undo()-ne.
    We are queueing a render of version `workflow.last_delta_id`, which may or
    may not be `delta.id`.
    """
    if delta.command_name == SetStepDataVersion.__name__:
        # SetStepDataVersion is often created from a fetch, and fetches
        # are often invoked by cron. These can be our most resource-intensive
        # operations: e.g., Twitter-accumulate with 1M records. So let's use
        # lazy rendering.
        #
        # From our point of view:
        #
        #     * If workflow has notifications, render.
        #     * If anybody is viewing workflow right now, render.
        #
        # Of course, it's impossible for us to know whether anybody is viewing
        # workflow. So we _broadcast_ to them and ask _them_ to request a
        # render if they're listening. This gives N render requests (one per
        # Websockets cconsumer) instead of 1, but we assume the extra render
        # requests will be no-ops.
        #
        # From the user's point of view:
        #
        #     * If I'm viewing workflow, changing data versions causes a
        #       render. (There isn't even any HTTP traffic: the consumer does
        #       the work.)
        #     * Otherwise, the next time I browse to the page, the page-load
        #       will request a render.
        #
        # Assumptions:
        #
        #     * Websockets consumers queue a render when we ask them.
        #     * The Django page-load view queues a render when needed.
        if await _workflow_has_notifications(workflow_id):
            await queue_render(workflow_id, relevant_delta_id)
        else:
            await rabbitmq.queue_render_if_consumers_are_listening(
                workflow_id, relevant_delta_id
            )
    else:
        # Normal case: the Delta says we need a render. Assume there's a user
        # waiting for this render -- otherwise, how did the Delta get here?
        await queue_render(workflow_id, relevant_delta_id)


@database_sync_to_async
def _first_forward_and_save_returning_clientside_update(
    cls, workflow_id: int, **kwargs
) -> Tuple[Optional[Delta], Optional[clientside.Update], bool]:
    """
    Create and execute `cls` command; return `(Delta, WebSocket data, render?)`.

    If `amend_create_kwargs()` returns `None`, return `(None, None)` here.

    All this, in a cooperative lock.

    Return `(None, None, False)` if `cls.amend_create_kwargs()` returns `None`.
    This is how `cls.amend_create_kwargs()` suggests the Delta should not be
    created at all.
    """
    command = NAME_TO_COMMAND[cls.__name__]
    # raises Workflow.DoesNotExist
    with Workflow.lookup_and_cooperative_lock(id=workflow_id) as workflow_lock:
        workflow = workflow_lock.workflow
        create_kwargs = command.amend_create_kwargs(workflow=workflow, **kwargs)
        if not create_kwargs:
            return (None, None, False)

        # Lookup unapplied deltas to delete. That's the head of the linked
        # list that comes _after_ `workflow.last_delta`.
        orphan_delta: Optional[Delta] = Delta.objects.filter(
            prev_delta_id=workflow.last_delta_id
        ).first()
        if orphan_delta:
            orphan_delta.delete_with_successors()

        delta = Delta.objects.create(
            command_name=cls.__name__,
            prev_delta_id=workflow.last_delta_id,
            **create_kwargs,
        )
        command.forward(delta)

        if orphan_delta:
            # We just deleted deltas; now we can garbage-collect Tabs and
            # Steps that are soft-deleted and have no deltas referring
            # to them.
            workflow.delete_orphan_soft_deleted_models()

        # Point workflow to us
        workflow.last_delta = delta
        workflow.updated_at = timezone.now()
        workflow.save(update_fields=["last_delta_id", "updated_at"])

        return (
            delta,
            command.load_clientside_update(delta),
            command.get_modifies_render_output(delta),
        )


@database_sync_to_async
def _call_forward_and_load_clientside_update(
    delta: Delta,
) -> Tuple[clientside.Update, bool]:
    with Workflow.lookup_and_cooperative_lock(id=delta.workflow_id):
        command = NAME_TO_COMMAND[delta.command_name]
        command.forward(delta)
        delta.workflow.last_delta = delta
        delta.workflow.updated_at = timezone.now()
        delta.workflow.save(update_fields=["last_delta_id", "updated_at"])

        return (
            command.load_clientside_update(delta),
            command.get_modifies_render_output(delta),
        )


@database_sync_to_async
def _call_backward_and_load_clientside_update(
    delta: Delta,
) -> Tuple[clientside.Update, bool]:
    with Workflow.lookup_and_cooperative_lock(id=delta.workflow_id):
        command = NAME_TO_COMMAND[delta.command_name]
        command.backward(delta)

        # Point workflow to previous delta
        # Only update prev_delta_id: other columns may have been edited in
        # backward().
        delta.workflow.last_delta = delta.prev_delta
        delta.workflow.updated_at = timezone.now()
        delta.workflow.save(update_fields=["last_delta_id", "updated_at"])

        return (
            command.load_clientside_update(delta),
            command.get_modifies_render_output(delta),
        )


async def do(
    cls, *, workflow_id: int, mutation_id: Optional[str] = None, **kwargs
) -> Delta:
    """Create a Delta and run its Command's .forward().

    If `amend_create_kwargs()` returns `None`, no-op.

    If Delta suggests sending a clientside.Update data, send it over RabbitMQ
    and possibly schedule a render.

    Keyword arguments vary by cls, but `workflow_id` is always required.

    If the client provides a mutation ID to an API function, that function
    _must_ supply that `mutation_id` here. The client and server can't remain
    in sync without it.

    Example:

        delta = await commands.do(
            SetStepNote,
            workflow_id=step.workflow_id,
            mutation_id=mutation_id,
            # ... other kwargs
        )
        # now delta has been applied and committed to the database, and
        # websockets updates have been queued for each consumer.
    """
    (
        delta,
        update,
        want_render,
    ) = await _first_forward_and_save_returning_clientside_update(
        cls, workflow_id, **kwargs
    )

    # In order: notify websockets that things are busy, _then_ give
    # renderer the chance to notify websockets rendering is finished.
    if update:
        if mutation_id:
            update = update.replace_mutation_id(mutation_id)
        await websockets_notify(workflow_id, update)

    if want_render:
        await _maybe_queue_render(workflow_id, delta.id, delta)

    return delta


async def redo(delta: Delta) -> None:
    """Call delta.forward(); notify websockets and renderer."""
    # updates delta.workflow.last_delta_id (so querying it won't cause a DB lookup)
    update, want_render = await _call_forward_and_load_clientside_update(delta)
    await websockets_notify(delta.workflow_id, update)
    if want_render:
        # Assume delta.workflow is cached and will not cause a database request
        await _maybe_queue_render(delta.workflow_id, delta.id, delta)


async def undo(delta: Delta) -> None:
    """Call delta.backward(); notify websockets and renderer."""
    # updates delta.workflow.last_delta_id (so querying it won't cause a DB lookup)
    update, want_render = await _call_backward_and_load_clientside_update(delta)
    await websockets_notify(delta.workflow_id, update)
    if want_render:
        # Assume delta.workflow is cached and will not cause a database request
        await _maybe_queue_render(
            delta.workflow_id, delta.workflow.last_delta_id, delta
        )
