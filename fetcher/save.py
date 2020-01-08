import contextlib
from django.utils import timezone
from cjworkbench.sync import database_sync_to_async
from cjwkernel.types import FetchResult
from cjwstate import clientside, commands, storedobjects
from server import websockets
from cjwstate.models import WfModule, Workflow
from cjwstate.models.commands import ChangeDataVersionCommand


@contextlib.contextmanager
def _locked_wf_module(workflow_id: int, wf_module: WfModule):
    """
    Refresh wf_module from database and yield with workflow lock.

    Raise Workflow.DoesNotExist or WfModule.DoesNotExist in the event of a
    race. (Even soft-deleted WfModule or Tab raises WfModule.DoesNotExist,
    to simulate hard deletion -- because sooner or later soft-delete won't be
    a thing any more.)
    """
    # raise Workflow.DoesNotExist
    with Workflow.lookup_and_cooperative_lock(id=workflow_id):
        # raise WfModule.DoesNotExist
        wf_module.refresh_from_db()
        if wf_module.is_deleted or wf_module.tab.is_deleted:
            raise WfModule.DoesNotExist("soft-deleted")
        yield


async def _notify_websockets(workflow_id: int, wf_module: WfModule) -> None:
    """
    Send delta to client, syncing all `wf_module` fields fetcher can edit.
    """
    update = clientside.Update(
        steps={
            wf_module.id: clientside.StepUpdate(
                is_busy=wf_module.is_busy, last_fetched_at=wf_module.last_update_check
            )
        }
    )
    await websockets.send_update_to_workflow_clients(workflow_id, update)


@database_sync_to_async
def _do_create_result(
    workflow_id: int, wf_module: WfModule, result: FetchResult, now: timezone.datetime
) -> None:
    """
    Do database manipulations for create_result().

    Modify `wf_module` in-place.

    Do *not* do the logic in ChangeDataVersionCommand. We're creating a new
    version, not doing something undoable.

    Raise WfModule.DoesNotExist or Workflow.DoesNotExist in case of a race.
    """
    error = ""
    if result.errors:
        if result.errors[0].message.id != "TODO_i18n":
            raise RuntimeError("TODO handle i18n-ready fetch-result errors")
        elif result.errors[0].quick_fixes:
            raise RuntimeError("TODO handle quick fixes from fetches")
        else:
            error = result.errors[0].message.args["text"]

    with _locked_wf_module(workflow_id, wf_module):
        storedobjects.create_stored_object(
            workflow_id, wf_module.id, result.path, stored_at=now
        )
        storedobjects.enforce_storage_limits(wf_module)

        wf_module.fetch_error = error
        wf_module.is_busy = False
        wf_module.last_update_check = now
        wf_module.save(update_fields=["fetch_error", "is_busy", "last_update_check"])


async def create_result(
    workflow_id: int, wf_module: WfModule, result: FetchResult, now: timezone.datetime
) -> None:
    """
    Store fetched table as storedobject..

    Set `fetch_error` to `result.error`. Set `is_busy` to `False`. Set
    `last_update_check`.

    Create (and run) a ChangeDataVersionCommand. This will kick off an execute
    cycle, which will render each module and email the owner if data has
    changed and notifications are enabled.

    Notify the user over Websockets.

    No-op if `workflow` or `wf_module` has been deleted.
    """
    try:
        await _do_create_result(workflow_id, wf_module, result, now)
    except (WfModule.DoesNotExist, Workflow.DoesNotExist):
        return  # there's nothing more to do

    # ChangeDataVersionCommand will change `wf_module.last_relevant_delta_id`.
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
        wf_module=wf_module,
        new_version=now,
    )

    # XXX odd design: ChangeDataVersionCommand happens to update "versions"
    # on the client. So _notify_websockets() doesn't need to send the new
    # "versions".

    await _notify_websockets(workflow_id, wf_module)


@database_sync_to_async
def _do_mark_result_unchanged(
    workflow_id: int, wf_module: WfModule, now: timezone.datetime
) -> None:
    """
    Do database manipulations for mark_result_unchanged().

    Modify `wf_module` in-place.

    Raise WfModule.DoesNotExist or Workflow.DoesNotExist in case of a race.
    """
    with _locked_wf_module(workflow_id, wf_module):
        wf_module.is_busy = False
        wf_module.last_update_check = now
        wf_module.save(update_fields=["is_busy", "last_update_check"])


async def mark_result_unchanged(
    workflow_id: int, wf_module: WfModule, now: timezone.datetime
) -> None:
    """
    Leave storedobjects and `wf_module.fetch_error` unchanged.

    Set wf_module.is_busy to False.

    Set wf_module.last_update_check.

    Notify the user over Websockets.

    No-op if `workflow` or `wf_module` has been deleted.
    """
    try:
        await _do_mark_result_unchanged(workflow_id, wf_module, now)
    except (WfModule.DoesNotExist, Workflow.DoesNotExist):
        return  # there's nothing more to do

    await _notify_websockets(workflow_id, wf_module)
