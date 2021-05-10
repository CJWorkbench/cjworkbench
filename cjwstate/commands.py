"""do(), undo() and redo(): commands that change a Workflow.

A Workflow's history looks like this:

    v1  --d1-->  v2  --d2-->  v3  --d3-->  v4  ...

A Delta comes "between" two versions. These Deltas -- d1, d2, d3 -- are the
Workflow's "delta chain".

To find a Workflow's (conceptual) version, look at `workflow.last_delta_id`. If
it's `d1.id`, the Workflow is at version v2. If it's `d3.id`, the Workflow is at
version v4.

To complicate matters a bit, we're allowed to _delete_ Deltas. (This helps us
expunge old records, so we can nix obsolete code.) We may delete the last Delta
in a chain if it comes after the Workflow version. We may delete the first
Delta in a chain if it comes before the Workflow version.

A special case: imagine we're at v2 and we delete d1. Then
`workflow.last_delta_id` points to `d1.id`, but the Delta with ID `d1.id` no
longer exists! Don't panic: this is fine. Indeed, the default
`workflow.last_delta_id` is 0.
"""
import datetime
from typing import Optional, Tuple

from cjworkbench.sync import database_sync_to_async
from cjwstate import clientside, rabbitmq
from cjwstate.models import Delta, Step, Workflow
from cjwstate.models.commands import NAME_TO_COMMAND, InitWorkflow, SetStepDataVersion


async def websockets_notify(workflow_id: int, update: clientside.Update) -> None:
    """Notify Websockets clients of `update`; return immediately.

    This is an alias; its main purpose is for white-box unit testing.
    """
    await rabbitmq.send_update_to_workflow_clients(workflow_id, update)


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
            await rabbitmq.queue_render(workflow_id, relevant_delta_id)
        else:
            await rabbitmq.queue_render_if_consumers_are_listening(
                workflow_id, relevant_delta_id
            )
    else:
        # Normal case: the Delta says we need a render. Assume there's a user
        # waiting for this render -- otherwise, how did the Delta get here?
        await rabbitmq.queue_render(workflow_id, relevant_delta_id)


@database_sync_to_async
def _first_forward_and_save_returning_clientside_update(
    cls, workflow_id: int, **kwargs
) -> Tuple[Optional[Delta], Optional[clientside.Update], Optional[int]]:
    """
    Create and execute `cls` command; return `(Delta, WebSocket data, render?)`.

    If `amend_create_kwargs()` returns `None`, return `(None, None)` here.

    All this, in a cooperative lock.

    Return `(None, None, None)` if `cls.amend_create_kwargs()` returns `None`.
    This is how `cls.amend_create_kwargs()` suggests the Delta should not be
    created at all.
    """
    now = datetime.datetime.now()
    command = NAME_TO_COMMAND[cls.__name__]
    try:
        # raise Workflow.DoesNotExist
        with Workflow.lookup_and_cooperative_lock(id=workflow_id) as workflow_lock:
            workflow = workflow_lock.workflow
            create_kwargs = command.amend_create_kwargs(workflow=workflow, **kwargs)
            if not create_kwargs:
                return None, None, None

            # Lookup unapplied deltas to delete. That's the linked list that comes
            # _after_ `workflow.last_delta_id`.
            n_deltas_deleted, _ = workflow.deltas.filter(
                id__gt=workflow.last_delta_id
            ).delete()

            # prev_delta is none when we're at the start of the undo stack
            prev_delta = workflow.deltas.filter(id=workflow.last_delta_id).first()

            # Delta.objects.create() and command.forward() may raise unexpected errors
            # Defer delete_orphan_soft_deleted_models(), to reduce the risk of this
            # race: 1. Delete DB objects; 2. Delete S3 files; 3. ROLLBACK. (We aren't
            # avoiding the race _entirely_ here, but we're at least avoiding causing
            # the race through errors in Delta or Command.)
            delta = Delta.objects.create(
                command_name=cls.__name__,
                prev_delta=prev_delta,
                last_applied_at=now,
                **create_kwargs,
            )
            command.forward(delta)

            # Point workflow to us
            workflow.last_delta_id = delta.id
            workflow.updated_at = datetime.datetime.now()
            workflow.save(update_fields=["last_delta_id", "updated_at"])

            if n_deltas_deleted:
                # We just deleted deltas; now we can garbage-collect Tabs and
                # Steps that are soft-deleted and have no deltas referring
                # to them.
                workflow.delete_orphan_soft_deleted_models()

            return (
                delta,
                command.load_clientside_update(delta),
                delta.id if command.get_modifies_render_output(delta) else None,
            )
    except Workflow.DoesNotExist:
        return None, None, None


@database_sync_to_async
def _call_forward_and_load_clientside_update(
    workflow_id: int,
) -> Tuple[Optional[Delta], Optional[clientside.Update], Optional[int]]:
    now = datetime.datetime.now()

    try:
        with Workflow.lookup_and_cooperative_lock(id=workflow_id) as workflow_lock:
            workflow = workflow_lock.workflow

            delta = workflow.deltas.filter(id__gt=workflow.last_delta_id).first()
            if delta is None:
                # Nothing to redo: we're at the end of the delta chain
                return None, None, None

            command = NAME_TO_COMMAND[delta.command_name]
            command.forward(delta)

            workflow.last_delta_id = delta.id
            workflow.updated_at = now
            workflow.save(update_fields=["last_delta_id", "updated_at"])

            delta.last_applied_at = now
            delta.save(update_fields=["last_applied_at"])

            return (
                delta,
                command.load_clientside_update(delta),
                delta.id if command.get_modifies_render_output(delta) else None,
            )
    except Workflow.DoesNotExist:
        return None, None, None


@database_sync_to_async
def _call_backward_and_load_clientside_update(
    workflow_id: int,
) -> Tuple[Optional[Delta], Optional[clientside.Update], Optional[int]]:
    now = datetime.datetime.now()

    try:
        with Workflow.lookup_and_cooperative_lock(id=workflow_id) as workflow_lock:
            workflow = workflow_lock.workflow
            # raise Delta.DoesNotExist if we're at the beginning of the undo chain
            delta = workflow.deltas.exclude(command_name=InitWorkflow.__name__).get(
                id=workflow.last_delta_id
            )

            command = NAME_TO_COMMAND[delta.command_name]
            command.backward(delta)

            # Point workflow to previous delta
            # Only update prev_delta_id: other columns may have been edited in
            # backward().
            workflow.last_delta_id = delta.prev_delta_id or 0
            workflow.updated_at = now
            workflow.save(update_fields=["last_delta_id", "updated_at"])

            delta.last_applied_at = now
            delta.save(update_fields=["last_applied_at"])

            return (
                delta,
                command.load_clientside_update(delta),
                (
                    workflow.last_delta_id
                    if command.get_modifies_render_output(delta)
                    else None
                ),
            )
    except (Workflow.DoesNotExist, Delta.DoesNotExist):
        return None, None, None


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
        render_delta_id,
    ) = await _first_forward_and_save_returning_clientside_update(
        cls, workflow_id, **kwargs
    )

    # In order: notify websockets that things are busy, _then_ give
    # renderer the chance to notify websockets rendering is finished.
    if update is not None:
        if mutation_id:
            update = update.replace_mutation_id(mutation_id)
        await websockets_notify(workflow_id, update)

    if render_delta_id is not None:
        await _maybe_queue_render(workflow_id, render_delta_id, delta)

    return delta


async def redo(workflow_id: int) -> None:
    """Call delta.forward(); notify websockets and renderer.

    No-op if there is no Delta to redo.
    """
    # updates delta.workflow.last_delta_id (so querying it won't cause a DB lookup)
    delta, update, render_delta_id = await _call_forward_and_load_clientside_update(
        workflow_id
    )
    if update is not None:
        await websockets_notify(workflow_id, update)
    if render_delta_id is not None:
        # Assume delta.workflow is cached and will not cause a database request
        await _maybe_queue_render(workflow_id, render_delta_id, delta)


async def undo(workflow_id: int) -> None:
    """Call delta.backward(); notify websockets and renderer.

    No-op if there is no Delta to undo.
    """
    # updates delta.workflow.last_delta_id (so querying it won't cause a DB lookup)
    delta, update, render_delta_id = await _call_backward_and_load_clientside_update(
        workflow_id
    )
    if update is not None:
        await websockets_notify(workflow_id, update)
    if render_delta_id is not None:
        # Assume delta.workflow is cached and will not cause a database request
        await _maybe_queue_render(workflow_id, render_delta_id, delta)
