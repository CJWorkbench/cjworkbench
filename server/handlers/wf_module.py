import asyncio
import datetime
import functools
import secrets
from typing import Any, Dict, List, Optional
from dateutil.parser import isoparse
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from cjworkbench.sync import database_sync_to_async
from server import oauth, rabbitmq, websockets
from cjwstate.models import Workflow, WfModule
from cjwstate.models.commands import (
    ChangeParametersCommand,
    DeleteModuleCommand,
    ChangeDataVersionCommand,
    ChangeWfModuleNotesCommand,
)
from cjwstate.models.param_spec import ParamSpec
import server.utils
from . import autofetch
from .types import HandlerError
from .decorators import register_websockets_handler, websockets_handler


class AutofetchQuotaExceeded(Exception):
    def __init__(self, autofetches):
        self.autofetches = autofetches


def _postgresize_dict_in_place(d: Dict[str, Any]) -> None:
    """
    Modify `d` so it's ready to be inserted in a Postgres JSONB column.

    Modifications:
        * `"\u0000"` is replaced with `""`
    """
    # modify in iterator -- scary, but not wrong since order is guaranteed and
    # we aren't inserting or deleting items. ref:
    # https://docs.python.org/3/library/stdtypes.html#dictionary-view-objects
    for key, value in d.items():
        if isinstance(value, list):
            _postgresize_list_in_place(value)
        elif isinstance(value, dict):
            _postgresize_dict_in_place(value)
        elif isinstance(value, str):
            d[key] = _postgresize_str(value)
        # else don't modify it


def _postgresize_list_in_place(l: List[Any]) -> None:
    """
    Modify `l` so it's ready to be inserted in a Postgres JSONB column.

    Modifications:
        * `"\u0000"` is replaced with `""`
    """
    # modify in iterator -- scary, but not wrong since order is guaranteed and
    # we aren't inserting or deleting items.
    for i, value in enumerate(l):
        if isinstance(value, list):
            _postgresize_list_in_place(value)
        elif isinstance(value, dict):
            _postgresize_dict_in_place(value)
        elif isinstance(value, str):
            l[i] = _postgresize_str(value)
        # else don't modify it


def _postgresize_str(s: str) -> str:
    """
    Modify `l` so it's ready to be inserted in a Postgres JSONB column.

    Modifications:
        * `"\u0000"` is replaced with `""`
    """
    return s.replace("\x00", "")


@database_sync_to_async
def _load_wf_module(workflow: Workflow, wf_module_id: int) -> WfModule:
    """Returns a WfModule or raises HandlerError."""
    try:
        return WfModule.live_in_workflow(workflow).get(id=wf_module_id)
    except WfModule.DoesNotExist:
        raise HandlerError("DoesNotExist: WfModule not found")


def _loading_wf_module(func):
    @functools.wraps(func)
    async def inner(workflow: Workflow, wfModuleId: int, **kwargs):
        wf_module = await _load_wf_module(workflow, wfModuleId)
        return await func(workflow=workflow, wf_module=wf_module, **kwargs)

    return inner


@register_websockets_handler
@websockets_handler("write")
@_loading_wf_module
async def set_params(
    workflow: Workflow, wf_module: WfModule, values: Dict[str, Any], **kwargs
):
    if not isinstance(values, dict):
        raise HandlerError("BadRequest: values must be an Object")

    # Mangle user data by removing '\u0000' recursively: Postgres `JSONB`
    # doesn't support \u0000, and it's too expensive (and questionable) to move
    # to `JSON`. https://www.pivotaltracker.com/story/show/164634811
    _postgresize_dict_in_place(values)

    try:
        await ChangeParametersCommand.create(
            workflow=workflow, wf_module=wf_module, new_values=values
        )
    except ValueError as err:
        raise HandlerError("ValueError: " + str(err))


@register_websockets_handler
@websockets_handler("write")
@_loading_wf_module
async def delete(workflow: Workflow, wf_module: WfModule, **kwargs):
    await DeleteModuleCommand.create(workflow=workflow, wf_module=wf_module)


@database_sync_to_async
def _find_precise_version(
    wf_module: WfModule, version: datetime.datetime
) -> datetime.datetime:
    # TODO maybe let's not use microsecond-precision numbers as
    # StoredObject IDs and then send the client
    # millisecond-precision identifiers. We _could_ just pass
    # clients the IDs, for instance.
    #
    # Select a version within 1ms of the (rounded _or_ truncated)
    # version we sent the client.
    #
    # (Let's not change the way we JSON-format dates just to avoid
    # this hack. That would be even worse.)
    try:
        return wf_module.stored_objects.filter(
            stored_at__gte=version - datetime.timedelta(microseconds=500),
            stored_at__lt=version + datetime.timedelta(milliseconds=1),
        ).values_list("stored_at", flat=True)[0]
    except IndexError:
        return version


@database_sync_to_async
def _mark_stored_object_read(wf_module: WfModule, version: datetime.datetime) -> None:
    wf_module.stored_objects.filter(stored_at=version).update(read=True)


@register_websockets_handler
@websockets_handler("write")
@_loading_wf_module
async def set_stored_data_version(
    workflow: Workflow, wf_module: WfModule, version: str, **kwargs
):
    try:
        # cast to str: dateutil.parser may have vulnerability with non-str
        version = str(version)
        version = isoparse(version)
    except (ValueError, OverflowError, TypeError):
        raise HandlerError("BadRequest: version must be an ISO8601 datetime")

    version = await _find_precise_version(wf_module, version)

    await ChangeDataVersionCommand.create(
        workflow=workflow, wf_module=wf_module, new_version=version
    )

    await _mark_stored_object_read(wf_module, version)


@register_websockets_handler
@websockets_handler("write")
@_loading_wf_module
async def set_notes(workflow: Workflow, wf_module: WfModule, notes: str, **kwargs):
    notes = str(notes)  # cannot error from JSON input
    await ChangeWfModuleNotesCommand.create(
        workflow=workflow, wf_module=wf_module, new_value=notes
    )


@database_sync_to_async
def _do_set_collapsed(wf_module: WfModule, is_collapsed: bool):
    wf_module.is_collapsed = is_collapsed
    wf_module.save(update_fields=["is_collapsed"])


@register_websockets_handler
@websockets_handler("write")
@_loading_wf_module
async def set_collapsed(
    workflow: Workflow, wf_module: WfModule, isCollapsed: bool, **kwargs
):
    is_collapsed = bool(isCollapsed)  # cannot error from JSON input
    await _do_set_collapsed(wf_module, is_collapsed)


@database_sync_to_async
def _do_set_notifications(scope, wf_module: WfModule, notifications: bool):
    wf_module.notifications = notifications
    wf_module.save(update_fields=["notifications"])
    if notifications:
        server.utils.log_user_event_from_scope(
            scope, "Enabled email notifications", {"wfModuleId": wf_module.id}
        )


@register_websockets_handler
@websockets_handler("owner")
@_loading_wf_module
async def set_notifications(
    workflow: Workflow, wf_module: WfModule, notifications: bool, scope, **kwargs
):
    notifications = bool(notifications)  # cannot error from JSON input
    await _do_set_notifications(scope, wf_module, notifications)


@database_sync_to_async
def _do_clear_unseen_notification(wf_module: WfModule):
    wf_module.has_unseen_notification = False
    wf_module.save(update_fields=["has_unseen_notification"])


@register_websockets_handler
@websockets_handler("write")
@_loading_wf_module
async def clear_unseen_notifications(wf_module: WfModule, **kwargs):
    await _do_clear_unseen_notification(wf_module)


@database_sync_to_async
def _do_try_set_autofetch(
    scope, wf_module: WfModule, auto_update_data: bool, update_interval: int
):
    # We may ROLLBACK; if we do, we need to remember the old values
    old_auto_update_data = wf_module.auto_update_data
    old_update_interval = wf_module.update_interval

    check_quota = (
        auto_update_data
        and wf_module.auto_update_data
        and update_interval < wf_module.update_interval
    ) or (auto_update_data and not wf_module.auto_update_data)

    quota_exceeded = None
    try:
        with transaction.atomic():
            wf_module.auto_update_data = auto_update_data
            wf_module.update_interval = update_interval
            if auto_update_data:
                wf_module.next_update = timezone.now() + datetime.timedelta(
                    seconds=update_interval
                )
            else:
                wf_module.next_update = None
            wf_module.save(
                update_fields=["auto_update_data", "update_interval", "next_update"]
            )

            # Now before we commit, let's see if we've surpassed the user's limit;
            # roll back if we have.
            #
            # Only rollback if we're _increasing_ our fetch count. If we're
            # lowering it, allow that -- even if the user is over limit, we still
            # want to commit because it's an improvement.
            if check_quota:
                autofetches = autofetch.list_autofetches_json(scope)
                if autofetches["nFetchesPerDay"] > autofetches["maxFetchesPerDay"]:
                    raise AutofetchQuotaExceeded(autofetches)
    except AutofetchQuotaExceeded as err:
        wf_module.auto_update_data = old_auto_update_data
        wf_module.update_interval = old_update_interval
        quota_exceeded = err.autofetches

    retval = {
        "isAutofetch": wf_module.auto_update_data,
        "fetchInterval": wf_module.update_interval,
    }
    if quota_exceeded is not None:
        retval["quotaExceeded"] = quota_exceeded  # a dict
    return retval


@register_websockets_handler
@websockets_handler("owner")
@_loading_wf_module
async def try_set_autofetch(
    wf_module: WfModule, isAutofetch: bool, fetchInterval: int, scope, **kwargs
):
    auto_update_data = bool(isAutofetch)
    try:
        update_interval = max(settings.MIN_AUTOFETCH_INTERVAL, int(fetchInterval))
    except (ValueError, TypeError):
        return HandlerError("BadRequest: fetchInterval must be an integer")
    return await _do_try_set_autofetch(
        scope, wf_module, auto_update_data, update_interval
    )


@database_sync_to_async
def _set_wf_module_busy(wf_module):
    wf_module.is_busy = True
    wf_module.save(update_fields=["is_busy"])


@register_websockets_handler
@websockets_handler("write")
@_loading_wf_module
async def fetch(workflow: Workflow, wf_module: WfModule, **kwargs):
    await _set_wf_module_busy(wf_module)
    await rabbitmq.queue_fetch(workflow.id, wf_module.id)
    await websockets.ws_client_send_delta_async(
        workflow.id,
        {"updateWfModules": {str(wf_module.id): {"is_busy": True, "fetch_error": ""}}},
    )


@database_sync_to_async
def _lookup_service(wf_module: WfModule, param: str) -> oauth.OAuthService:
    """
    Find the OAuthService that manages `param` on `wf_module`.

    Raise `HandlerError` if we cannot.
    """
    module_version = wf_module.module_version
    if module_version is None:
        raise HandlerError("BadRequest: module {wf_module.module_id_name} not found")
    for field in module_version.param_fields:
        if (
            field.id_name == param
            and isinstance(field, ParamSpec.Secret)
            and isinstance(field.secret_logic, ParamSpec.Secret.Logic.Oauth)
        ):
            service_name = field.secret_logic.service
            service = oauth.OAuthService.lookup_or_none(service_name)
            if not service:
                allowed_services = ", ".join(settings.OAUTH_SERVICES.keys())
                raise HandlerError(f"AuthError: we only support {allowed_services}")
            return service
    else:
        raise HandlerError(
            f"Module {wf_module.module_id_name} has no oauth {param} parameter"
        )


@register_websockets_handler
@websockets_handler("owner")
@_loading_wf_module
async def generate_secret_access_token(
    workflow: Workflow, wf_module: WfModule, param: str, **kwargs
):
    """
    Return a temporary access_token the client can use.

    Only the owner can generate an access token: we must keep the secret away
    from prying eyes. This access token lets the client read all the owner's
    documents on GDrive.

    The response will look like:

        { "token": "asldkjfhalskdjfhas..." } -- success
        { "token": null } -- no value (or no param, even)
        { "error": "AuthError: ..." } -- access denied

    A typical caller should accept `null` but log other errors.
    """
    param = str(param)  # cannot generate an error from JSON params
    secrets = wf_module.secrets
    try:
        offline_token = secrets[param]["secret"]
    except TypeError:
        # secrets[param] is None
        return {"token": None}
    except KeyError:
        # There is no such secret param, or it is unset
        return {"token": None}
    except ValueError:
        # The param has the wrong type
        return {"token": None}
    if not offline_token:
        # Empty JSON -- no value has been set
        return {"token": None}

    service = await _lookup_service(wf_module, param)  # raise HandlerError
    # TODO make oauth async. In the meantime, move these HTTP requests to a
    # background thread.
    loop = asyncio.get_event_loop()
    func = functools.partial(service.generate_access_token_or_str_error, offline_token)
    token = await loop.run_in_executor(None, func)
    if isinstance(token, str):
        raise HandlerError(f"AuthError: {token}")

    # token['access_token'] is short-term (1hr). token['refresh_token'] is
    # super-private and we should never transmit it.
    return {"token": token["access_token"]}


@database_sync_to_async
def _wf_module_delete_secret_and_build_delta(
    workflow: Workflow, wf_module: WfModule, param: str
) -> Optional[Dict[str, Any]]:
    """
    Write a new secret (or `None`) to `wf_module`, or raise.

    Return a "delta" for websockets.ws_client_send_delta_async(), or `None` if
    the database has not been modified.

    Raise Workflow.DoesNotExist if the Workflow was deleted.
    """
    with workflow.cooperative_lock():  # raises Workflow.DoesNotExist
        try:
            wf_module.refresh_from_db()
        except WfModule.DoesNotExist:
            return None  # no-op

        if wf_module.secrets.get(param) is None:
            return None  # no-op

        wf_module.secrets = dict(wf_module.secrets)  # shallow copy
        del wf_module.secrets[param]
        wf_module.save(update_fields=["secrets"])

        return {
            "updateWfModules": {
                str(wf_module.id): {"secrets": wf_module.secret_metadata}
            }
        }


@register_websockets_handler
@websockets_handler("owner")
@_loading_wf_module
async def delete_secret(workflow: Workflow, wf_module: WfModule, param: str, **kwargs):
    delta = await _wf_module_delete_secret_and_build_delta(workflow, wf_module, param)
    if delta:
        await websockets.ws_client_send_delta_async(workflow.id, delta)


@database_sync_to_async
def _wf_module_set_secret_and_build_delta(
    workflow: Workflow, wf_module: WfModule, param: str, secret: str
) -> Optional[Dict[str, Any]]:
    """
    Write a new secret to `wf_module`, or raise.

    Return a "delta" for websockets.ws_client_send_delta_async(), or `None` if
    the database is not modified.

    Raise Workflow.DoesNotExist if the Workflow was deleted.
    """
    with workflow.cooperative_lock():  # raises Workflow.DoesNotExist
        try:
            wf_module.refresh_from_db()
        except WfModule.DoesNotExist:
            return None  # no-op

        if wf_module.secrets.get(param, {}).get("secret") == secret:
            return None  # no-op

        module_version = wf_module.module_version
        if module_version is None:
            raise HandlerError(f"BadRequest: ModuleVersion does not exist")
        if not any(
            p.type == "secret" and p.secret_logic.provider == "string"
            for p in module_version.param_fields
        ):
            raise HandlerError(f"BadRequest: param is not a secret string parameter")

        created_at = timezone.now()
        created_at_str = (
            created_at.strftime("%Y-%m-%dT%H:%M:%S")
            + "."
            + created_at.strftime("%f")[0:3]  # milliseconds
            + "Z"
        )

        wf_module.secrets = {
            **wf_module.secrets,
            param: {"name": created_at_str, "secret": secret},
        }
        wf_module.save(update_fields=["secrets"])

        return {
            "updateWfModules": {
                str(wf_module.id): {"secrets": wf_module.secret_metadata}
            }
        }


@register_websockets_handler
@websockets_handler("owner")
@_loading_wf_module
async def set_secret(
    workflow: Workflow, wf_module: WfModule, param: str, secret: str, **kwargs
):
    """
    Set a secret value `secret` on param `param`.

    `param` must point to a `secret` parameter with
    `secret_logic.provider == 'string'`. The server will set the `name` to
    the ISO8601-formatted representation of the current time, if `secret` is
    set to something new.
    """
    # Be safe with types
    param = str(param)
    secret = str(secret)
    delta = await _wf_module_set_secret_and_build_delta(
        workflow, wf_module, param, secret
    )

    if delta:
        await websockets.ws_client_send_delta_async(workflow.id, delta)


@database_sync_to_async
def _do_set_file_upload_api_token(wf_module: WfModule, api_token: Optional[str]):
    wf_module.file_upload_api_token = api_token
    wf_module.save(update_fields=["file_upload_api_token"])


@register_websockets_handler
@websockets_handler("write")
@_loading_wf_module
async def get_file_upload_api_token(workflow: Workflow, wf_module: WfModule, **kwargs):
    """
    Query the file-upload API token.

    We do not pass this token in Deltas, since only writers can see it. (As of
    [2019-08-05], Deltas aren't tailored to individual listeners' permissions.)
    """
    return {"apiToken": wf_module.file_upload_api_token}


@register_websockets_handler
@websockets_handler("write")
@_loading_wf_module
async def reset_file_upload_api_token(
    workflow: Workflow, wf_module: WfModule, **kwargs
):
    api_token = secrets.token_urlsafe()
    await _do_set_file_upload_api_token(wf_module, api_token)
    return {"apiToken": api_token}


@register_websockets_handler
@websockets_handler("write")
@_loading_wf_module
async def clear_file_upload_api_token(
    workflow: Workflow, wf_module: WfModule, **kwargs
):
    await _do_set_file_upload_api_token(wf_module, None)
