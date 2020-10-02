import contextlib
from django.utils import timezone
from cjworkbench.sync import database_sync_to_async
from cjwkernel.types import FetchResult
from cjwstate import clientside, commands, rabbitmq, storedobjects
from cjwstate.models import Step, Workflow
from cjwstate.models.commands import ChangeDataVersionCommand


@contextlib.contextmanager
def _locked_step(workflow_id: int, step: Step):
    """Refresh step from database and yield with workflow lock.

    Raise Workflow.DoesNotExist or Step.DoesNotExist in the event of a
    race. (Even soft-deleted Step or Tab raises Step.DoesNotExist,
    to simulate hard deletion -- because sooner or later soft-delete won't be
    a thing any more.)
    """
    # raise Workflow.DoesNotExist
    with Workflow.lookup_and_cooperative_lock(id=workflow_id):
        # raise Step.DoesNotExist
        step.refresh_from_db()
        if step.is_deleted or step.tab.is_deleted:
            raise Step.DoesNotExist("soft-deleted")
        yield


async def _notify_websockets(workflow_id: int, step: Step) -> None:
    """Send delta to client, syncing all `step` fields fetcher can edit."""
    update = clientside.Update(
        steps={
            step.id: clientside.StepUpdate(
                is_busy=step.is_busy, last_fetched_at=step.last_update_check
            )
        }
    )
    await rabbitmq.send_update_to_workflow_clients(workflow_id, update)


@database_sync_to_async
def _do_create_result(
    workflow_id: int, step: Step, result: FetchResult, now: timezone.datetime
) -> None:
    """Do database manipulations for create_result().

    Modify `step` in-place.

    Do *not* do the logic in ChangeDataVersionCommand. We're creating a new
    version, not doing something undoable.

    Raise Step.DoesNotExist or Workflow.DoesNotExist in case of a race.
    """
    with _locked_step(workflow_id, step):
        storedobjects.create_stored_object(
            workflow_id, step.id, result.path, stored_at=now
        )
        storedobjects.enforce_storage_limits(step)

        step.fetch_errors = result.errors
        step.is_busy = False
        step.last_update_check = now
        step.save(update_fields=["fetch_errors", "is_busy", "last_update_check"])


async def create_result(
    workflow_id: int, step: Step, result: FetchResult, now: timezone.datetime
) -> None:
    """Store fetched table as storedobject..

    Set `fetch_errors` to `result.errors`. Set `is_busy` to `False`. Set
    `last_update_check`.

    Create (and run) a ChangeDataVersionCommand. This will kick off an execute
    cycle, which will render each module and email the owner if data has
    changed and notifications are enabled.

    Notify the user over Websockets.

    No-op if `workflow` or `step` has been deleted.
    """
    try:
        await _do_create_result(workflow_id, step, result, now)
    except (Step.DoesNotExist, Workflow.DoesNotExist):
        return  # there's nothing more to do

    # ChangeDataVersionCommand will change `step.last_relevant_delta_id`.
    # This must happen before we notify with our own `is_busy=False`, to avoid
    # this erroneous ordering of Websockets messages:
    #
    # A. is_busy=True -- we acknowledge the user's fetch request
    # C. is_busy=False -- we're done fetching
    # B. new last_relevant_delta_id -- a render is pending
    #
    # If C comes before B, the client will flicker to a "not-busy" state.
    await commands.do(
        ChangeDataVersionCommand,
        workflow_id=workflow_id,
        step=step,
        new_version=now,
    )

    # XXX odd design: ChangeDataVersionCommand happens to update "versions"
    # on the client. So _notify_websockets() doesn't need to send the new
    # "versions".

    await _notify_websockets(workflow_id, step)


@database_sync_to_async
def _do_mark_result_unchanged(
    workflow_id: int, step: Step, now: timezone.datetime
) -> None:
    """Do database manipulations for mark_result_unchanged().

    Modify `step` in-place.

    Raise Step.DoesNotExist or Workflow.DoesNotExist in case of a race.
    """
    with _locked_step(workflow_id, step):
        step.is_busy = False
        step.last_update_check = now
        step.save(update_fields=["is_busy", "last_update_check"])


async def mark_result_unchanged(
    workflow_id: int, step: Step, now: timezone.datetime
) -> None:
    """Leave storedobjects and `step.fetch_errors` unchanged.

    Set step.is_busy to False.

    Set step.last_update_check.

    Notify the user over Websockets.

    No-op if `workflow` or `step` has been deleted.
    """
    try:
        await _do_mark_result_unchanged(workflow_id, step, now)
    except (Step.DoesNotExist, Workflow.DoesNotExist):
        return  # there's nothing more to do

    await _notify_websockets(workflow_id, step)
