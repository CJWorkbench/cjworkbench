from typing import Any, Dict, Optional, Tuple
from cjworkbench.sync import database_sync_to_async
from cjwstate.models import Delta, WfModule, Workflow
from cjwstate.models.commands import ChangeDataVersionCommand
from server import rabbitmq, websockets


async def websockets_notify(workflow_id: int, ws_data: Dict[str, Any]) -> None:
    """
    Notify Websockets clients of `ws_data`; return immediately.

    This is an alias; its main purpose is for white-box unit testing.
    """
    await websockets.ws_client_send_delta_async(workflow_id, ws_data)


async def queue_render(workflow_id: int, delta_id: int) -> None:
    """
    Tell renderer to render `workflow`; return immediately.

    This is an alias; its main purpose is for white-box unit testing.
    """
    await rabbitmq.queue_render(workflow_id, delta_id)


@database_sync_to_async
def _workflow_has_notifications(workflow: Workflow) -> bool:
    """Detect whether a workflow sends email on changes."""
    return WfModule.live_in_workflow(workflow).filter(notifications=True).exists()


async def _maybe_queue_render(workflow: Workflow, delta: Delta) -> None:
    """
    Tell renderer to render `workflow`; return immediately.

    `delta` is used to check for ChangeDataVersionCommand, which gets special
    logic. But to be clear: the `delta` in question might have been undo()-ne.
    We are queueing a render of version `workflow.last_delta_id`, which may or
    may not be `delta.id`.
    """
    if isinstance(delta, ChangeDataVersionCommand):
        # ChangeDataVersionCommand is often created from a fetch, and fetches
        # are often invoked by cron. These can be our most resource-intensive
        # operations: e.g., Twitter-accumulate with 1M records. So let's use
        # lazy rendering.
        #
        # From our point of view:
        #
        #     * If self.workflow has notifications, render.
        #     * If anybody is viewing self.workflow right now, render.
        #
        # Of course, it's impossible for us to know whether anybody is viewing
        # self.workflow. So we _broadcast_ to them and ask _them_ to request a
        # render if they're listening. This gives N render requests (one per
        # Websockets cconsumer) instead of 1, but we assume the extra render
        # requests will be no-ops.
        #
        # From the user's point of view:
        #
        #     * If I'm viewing self.workflow, changing data versions causes a
        #       render. (There isn't even any HTTP traffic: the consumer does
        #       the work.)
        #     * Otherwise, the next time I browse to the page, the page-load
        #       will request a render.
        #
        # Assumptions:
        #
        #     * Websockets consumers queue a render when we ask them.
        #     * The Django page-load view queues a render when needed.
        if await _workflow_has_notifications(workflow):
            await queue_render(workflow.id, workflow.last_delta_id)
        else:
            await websockets.queue_render_if_listening(
                workflow.id, workflow.last_delta_id
            )
    else:
        # Normal case: the Delta says we need a render. Assume there's a user
        # waiting for this render -- otherwise, how did the Delta get here?
        await queue_render(workflow.id, workflow.last_delta_id)


@database_sync_to_async
def _first_forward_and_save_returning_ws_data(
    cls, workflow: Workflow, **kwargs
) -> Tuple[Delta, Dict[str, Any], bool]:
    """
    Create and execute `cls` command; return `(Delta, WebSocket data, render?)`.

    If `amend_create_kwargs()` returns `None`, return `(None, None)` here.

    All this, in a cooperative lock.

    Return `(None, None, False)` if `cls.amend_create_kwargs()` returns `None`.
    This is how `cls.amend_create_kwargs()` suggests the Delta should not be
    created at all.
    """
    with workflow.cooperative_lock():
        create_kwargs = cls.amend_create_kwargs(workflow=workflow, **kwargs)
        if not create_kwargs:
            return (None, None, False)

        # Lookup unapplied deltas to delete. That's the head of the linked
        # list that comes _after_ `workflow.last_delta`.
        orphan_delta: Optional[Delta] = Delta.objects.filter(
            prev_delta_id=workflow.last_delta_id
        ).first()
        if orphan_delta:
            orphan_delta.delete_with_successors()

        delta = cls.objects.create(
            prev_delta_id=workflow.last_delta_id, **create_kwargs
        )
        delta.forward_impl()

        if orphan_delta:
            # We just deleted deltas; now we can garbage-collect Tabs and
            # WfModules that are soft-deleted and have no deltas referring
            # to them.
            workflow.delete_orphan_soft_deleted_models()

        # Point workflow to us
        workflow.last_delta = delta
        workflow.save(update_fields=["last_delta_id"])

        return (delta, delta.load_ws_data(), delta.get_modifies_render_output())


@database_sync_to_async
def _call_forward_and_load_ws_data(delta: Delta) -> Tuple[Dict[str, Any], bool]:
    workflow = delta.workflow
    with workflow.cooperative_lock():
        delta.forward_impl()
        workflow.last_delta = delta
        workflow.save(update_fields=["last_delta_id"])

        return (delta.load_ws_data(), delta.get_modifies_render_output())


@database_sync_to_async
def _call_backward_and_load_ws_data(delta: Delta) -> Tuple[Dict[str, Any], bool]:
    workflow = delta.workflow
    with workflow.cooperative_lock():
        delta.backward_impl()

        # Point workflow to previous delta
        # Only update prev_delta_id: other columns may have been edited in
        # backward_impl().
        workflow.last_delta = delta.prev_delta
        workflow.save(update_fields=["last_delta_id"])

        return (delta.load_ws_data(), delta.get_modifies_render_output())


async def do(cls, *, workflow: Workflow, **kwargs) -> Delta:
    """
    Create a Command and run its .forward().

    If `amend_create_kwargs()` returns `None`, no-op.

    If Delta suggests sending websockets data, send it over Websockets
    and possibly schedule a render.

    Keyword arguments vary by cls, but `workflow` is always required.

    Example:

        delta = await commands.do(
            ChangeWfModuleNotesCommand,
            workflow=wf_module.workflow, 
            # ... other kwargs
        )
        # now delta has been applied and committed to the database, and
        # websockets users have been notified.
    """
    delta, ws_data, want_render = await _first_forward_and_save_returning_ws_data(
        cls, workflow, **kwargs
    )

    # In order: notify websockets that things are busy, _then_ give
    # renderer the chance to notify websockets rendering is finished.
    if delta:
        await websockets_notify(workflow.id, ws_data)

    if want_render:
        await _maybe_queue_render(workflow, delta)

    return delta


async def redo(delta: Delta) -> None:
    """
    Call delta.forward_impl(); notify websockets and renderer.
    """
    ws_data, want_render = await _call_forward_and_load_ws_data(delta)
    if ws_data:
        await websockets_notify(delta.workflow_id, ws_data)
    if want_render:
        # Assume delta.workflow is cached and will not cause a database request
        await _maybe_queue_render(delta.workflow, delta)


async def undo(delta: Delta) -> None:
    """
    Call delta.backward_impl(); notify websockets and renderer.
    """
    ws_data, want_render = await _call_backward_and_load_ws_data(delta)
    if ws_data:
        await websockets_notify(delta.workflow_id, ws_data)
    if want_render:
        # Assume delta.workflow is cached and will not cause a database request
        await _maybe_queue_render(delta.workflow, delta)
