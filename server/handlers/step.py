import asyncio
import datetime
import functools
import secrets
from typing import Any, Dict, List, Optional

from cjwmodule.spec.paramfield import ParamField
from dateutil.parser import isoparse
from django.conf import settings

import server.utils
from cjworkbench.sync import database_sync_to_async
from cjwstate import clientside, commands, oauth, rabbitmq
from cjwstate.models.commands import (
    DeleteStep,
    SetStepDataVersion,
    SetStepNote,
    SetStepParams,
)
from cjwstate.models.dbutil import lock_user_by_id, query_user_usage
from cjwstate.models.module_registry import MODULE_REGISTRY
from cjwstate.models.step import Step
from cjwstate.models.workflow import Workflow
from . import autofetch
from .decorators import register_websockets_handler, websockets_handler
from .util import lock_workflow_for_role
from .types import HandlerError


class AutofetchQuotaExceeded(Exception):
    pass


def _postgresize_dict_in_place(d: Dict[str, Any]) -> None:
    """Modify `d` so it's ready to be inserted in a Postgres JSONB column.

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
    """Modify `l` so it's ready to be inserted in a Postgres JSONB column.

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
    """Modify `l` so it's ready to be inserted in a Postgres JSONB column.

    Modifications:
        * `"\u0000"` is replaced with `""`
    """
    return s.replace("\x00", "")


@database_sync_to_async
def _load_step_by_id(workflow: Workflow, step_id: int) -> Step:
    """Return a Step or raises HandlerError."""
    try:
        return Step.live_in_workflow(workflow).get(id=step_id)
    except Step.DoesNotExist:
        raise HandlerError("DoesNotExist: Step not found")


def _load_step_by_slug_sync(workflow: Workflow, step_slug: str) -> Step:
    """Return a Step or raise HandlerError."""
    try:
        return Step.live_in_workflow(workflow).get(slug=step_slug)
    except Step.DoesNotExist:
        raise HandlerError("DoesNotExist: Step not found")


_load_step_by_slug = database_sync_to_async(_load_step_by_slug_sync)


def _loading_step_by_id(func):
    @functools.wraps(func)
    async def inner(workflow: Workflow, stepId: int, **kwargs):
        step = await _load_step_by_id(workflow, int(stepId))
        return await func(workflow=workflow, step=step, **kwargs)

    return inner


def _loading_step_by_slug(func):
    @functools.wraps(func)
    async def inner(workflow: Workflow, stepSlug: str, **kwargs):
        step = await _load_step_by_slug(workflow, str(stepSlug))
        return await func(workflow=workflow, step=step, **kwargs)

    return inner


@register_websockets_handler
@websockets_handler("write")
@_loading_step_by_id
async def set_params(workflow: Workflow, step: Step, values: Dict[str, Any], **kwargs):
    if not isinstance(values, dict):
        raise HandlerError("BadRequest: values must be an Object")

    # Mangle user data by removing '\u0000' recursively: Postgres `JSONB`
    # doesn't support \u0000, and it's too expensive (and questionable) to move
    # to `JSON`. https://www.pivotaltracker.com/story/show/164634811
    _postgresize_dict_in_place(values)

    try:
        await commands.do(
            SetStepParams, workflow_id=workflow.id, step=step, new_values=values
        )
    except ValueError as err:
        raise HandlerError("ValueError: " + str(err))


@register_websockets_handler
@websockets_handler("write")
@_loading_step_by_id
async def delete(workflow: Workflow, step: Step, **kwargs):
    await commands.do(DeleteStep, workflow_id=workflow.id, step=step)


@register_websockets_handler
@websockets_handler("write")
@_loading_step_by_id
async def set_stored_data_version(
    workflow: Workflow, step: Step, version: str, **kwargs
):
    try:
        # cast to str: dateutil.parser may have vulnerability with non-str
        version = str(version)
        version = isoparse(version)
    except (ValueError, OverflowError, TypeError):
        raise HandlerError("BadRequest: version must be an ISO8601 String")

    await commands.do(
        SetStepDataVersion,
        workflow_id=workflow.id,
        step=step,
        new_version=version,
    )


@register_websockets_handler
@websockets_handler("write")
@_loading_step_by_id
async def set_notes(workflow: Workflow, step: Step, notes: str, **kwargs):
    notes = str(notes)  # cannot error from JSON input
    await commands.do(
        SetStepNote,
        workflow_id=workflow.id,
        step=step,
        new_value=notes,
    )


@database_sync_to_async
def _do_set_collapsed(step: Step, is_collapsed: bool):
    step.is_collapsed = is_collapsed
    step.save(update_fields=["is_collapsed"])


@register_websockets_handler
@websockets_handler("write")
@_loading_step_by_id
async def set_collapsed(workflow: Workflow, step: Step, isCollapsed: bool, **kwargs):
    is_collapsed = bool(isCollapsed)  # cannot error from JSON input
    await _do_set_collapsed(step, is_collapsed)


@database_sync_to_async
def _do_set_notifications(scope, step: Step, notifications: bool):
    step.notifications = notifications
    step.save(update_fields=["notifications"])


@register_websockets_handler
@websockets_handler("owner")
@_loading_step_by_id
async def set_notifications(
    workflow: Workflow, step: Step, notifications: bool, scope, **kwargs
):
    notifications = bool(notifications)  # cannot error from JSON input
    await _do_set_notifications(scope, step, notifications)
    if notifications:
        await server.utils.log_user_event_from_scope(
            scope, "Enabled email notifications", {"stepId": step.id}
        )


@database_sync_to_async
def _do_try_set_autofetch(
    scope,
    workflow: Workflow,
    step_slug: str,
    auto_update_data: bool,
    update_interval: int,
) -> Dict[str, Any]:
    with lock_workflow_for_role(workflow, scope, role="owner"):
        step = _load_step_by_slug_sync(workflow, step_slug)  # or raise HandlerError

        check_quota = (
            auto_update_data
            and step.auto_update_data
            and update_interval < step.update_interval
        ) or (auto_update_data and not step.auto_update_data)

        step.auto_update_data = auto_update_data
        step.update_interval = update_interval
        if auto_update_data:
            step.next_update = datetime.datetime.now() + datetime.timedelta(
                seconds=update_interval
            )
        else:
            step.next_update = None
        step.save(update_fields=["auto_update_data", "update_interval", "next_update"])

        workflow.recalculate_fetches_per_day()
        workflow.save(update_fields=["fetches_per_day"])

        # Locking after write is fine, because we haven't called COMMIT
        # yet so nobody else can tell the difference.
        lock_user_by_id(
            workflow.owner_id, for_write=True
        )  # we're overwriting user's (calculated) fetches_per_day
        usage = query_user_usage(workflow.owner_id)

        # Now before we commit, let's see if we've surpassed the user's limit;
        # roll back if we have.
        #
        # Only rollback if we're _increasing_ our fetch count. If we're
        # lowering it, allow that -- even if the user is over limit, we still
        # want to commit because it's an improvement.
        if check_quota:
            limit = workflow.owner.user_profile.effective_limits.max_fetches_per_day
            if usage.fetches_per_day > limit:
                raise AutofetchQuotaExceeded

    return step, usage


@register_websockets_handler
@websockets_handler(role=None)  # we'll check "owner" in _do_try_set_autofetch
async def try_set_autofetch(
    workflow: Workflow,
    stepSlug: str,
    isAutofetch: bool,
    fetchInterval: int,
    scope,
    **kwargs,
):
    """Set step's autofetch settings, or not; respond with temporary data.

    Client-side, the amalgam of races looks like:

        1. Submit form with these `try_set_autofetch()` parameters.
        2. Server sends three pieces of data in parallel:
            a. Update the client state's step
            b. Update the client state's user usage
            c. Respond "ok"
        3. Client waits for all three messages, and shows "busy" until then.
        4. Client resets the form (because the state holds correct data now).

    Unfortunately, our client/server mechanism doesn't have a way to wait for
    _both_ 2a and 2b. (We have a "mutation" mechanism, but it can only wait
    for 2a, not both 2a and 2b.) [2021-06-17] this problem occurs nowhere else
    in our codebase, so we aren't inspired to build a big solution.

    Our hack: we assume that in practice, the client will usually receive
    2a+2b+2c nearly at the same time (since RabbitMQ is fast and the Internet
    is slow). So the client (3) waits for 2c and then waits a fixed duration;
    then (4) assumes 2a and 2b have arrived and resets the form.
    """
    step_slug = str(stepSlug)
    auto_update_data = bool(isAutofetch)
    try:
        update_interval = max(settings.MIN_AUTOFETCH_INTERVAL, int(fetchInterval))
    except (ValueError, TypeError):
        return HandlerError("BadRequest: fetchInterval must be an integer")

    try:
        step, usage = await _do_try_set_autofetch(
            scope, workflow, step_slug, auto_update_data, update_interval
        )  # updates workflow, step
    except AutofetchQuotaExceeded:
        raise HandlerError("AutofetchQuotaExceeded")

    await rabbitmq.send_user_update_to_user_clients(
        workflow.owner_id, clientside.UserUpdate(usage=usage)
    )
    await rabbitmq.send_update_to_workflow_clients(
        workflow.id,
        clientside.Update(
            workflow=clientside.WorkflowUpdate(
                fetches_per_day=workflow.fetches_per_day
            ),
            steps={
                step.id: clientside.StepUpdate(
                    is_auto_fetch=step.auto_update_data,
                    fetch_interval=step.update_interval,
                )
            },
        ),
    )


@database_sync_to_async
def _set_step_busy(step):
    step.is_busy = True
    step.save(update_fields=["is_busy"])


@register_websockets_handler
@websockets_handler("write")
@_loading_step_by_id
async def fetch(workflow: Workflow, step: Step, **kwargs):
    await _set_step_busy(step)
    await rabbitmq.queue_fetch(workflow.id, step.id)
    await rabbitmq.send_update_to_workflow_clients(
        workflow.id,
        clientside.Update(steps={step.id: clientside.StepUpdate(is_busy=True)}),
    )


@database_sync_to_async
def _lookup_service(step: Step, param: str) -> oauth.OAuthService:
    """Find the OAuthService that manages `param` on `step`.

    Raise `HandlerError` if we cannot.
    """
    module_id = step.module_id_name
    try:
        module_zipfile = MODULE_REGISTRY.latest(module_id)
    except KeyError:
        raise HandlerError(f"BadRequest: module {module_id} not found")
    module_spec = module_zipfile.get_spec()
    for field in module_spec.param_fields:
        if (
            field.id_name == param
            and isinstance(field, ParamField.Secret)
            and (
                isinstance(field.secret_logic, ParamField.Secret.Logic.Oauth1a)
                or isinstance(field.secret_logic, ParamField.Secret.Logic.Oauth2)
            )
        ):
            service_name = field.secret_logic.service
            service = oauth.OAuthService.lookup_or_none(service_name)
            if not service:
                allowed_services = ", ".join(settings.OAUTH_SERVICES.keys())
                raise HandlerError(f"AuthError: we only support {allowed_services}")
            return service
    else:
        raise HandlerError(f"Module {module_id} has no oauth {param} parameter")


@register_websockets_handler
@websockets_handler("owner")
@_loading_step_by_id
async def generate_secret_access_token(
    workflow: Workflow, step: Step, param: str, **kwargs
):
    """Return a temporary access_token the client can use.

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
    secrets = step.secrets
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

    service = await _lookup_service(step, param)  # raise HandlerError
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
def _step_delete_secret_and_build_delta(
    workflow: Workflow, step: Step, param: str
) -> Optional[clientside.Update]:
    """Write a new secret (or `None`) to `step`, or raise.

    Return a `clientside.Update`, or `None` if the database is not modified.

    Raise Workflow.DoesNotExist if the Workflow was deleted.
    """
    with workflow.cooperative_lock():  # raises Workflow.DoesNotExist
        try:
            step.refresh_from_db()
        except Step.DoesNotExist:
            return None  # no-op

        if step.secrets.get(param) is None:
            return None  # no-op

        step.secrets = dict(step.secrets)  # shallow copy
        del step.secrets[param]
        step.save(update_fields=["secrets"])

        return clientside.Update(
            steps={step.id: clientside.StepUpdate(secrets=step.secret_metadata)}
        )


@register_websockets_handler
@websockets_handler("owner")
@_loading_step_by_id
async def delete_secret(workflow: Workflow, step: Step, param: str, **kwargs):
    update = await _step_delete_secret_and_build_delta(workflow, step, param)
    if update:
        await rabbitmq.send_update_to_workflow_clients(workflow.id, update)


@database_sync_to_async
def _step_set_secret_and_build_delta(
    workflow: Workflow, step: Step, param: str, secret: str
) -> Optional[clientside.Update]:
    """Write a new secret to `step`, or raise.

    Return a `clientside.Update`, or `None` if the database is not modified.

    Raise Workflow.DoesNotExist if the Workflow was deleted.
    """
    with workflow.cooperative_lock():  # raises Workflow.DoesNotExist
        try:
            step.refresh_from_db()
        except Step.DoesNotExist:
            return None  # no-op

        if step.secrets.get(param, {}).get("secret") == secret:
            return None  # no-op

        try:
            module_zipfile = MODULE_REGISTRY.latest(step.module_id_name)
        except KeyError:
            raise HandlerError(
                f"BadRequest: ModuleZipfile {step.module_id_name} does not exist"
            )
        module_spec = module_zipfile.get_spec()
        if not any(
            p.type == "secret" and p.secret_logic.provider == "string"
            for p in module_spec.param_fields
        ):
            raise HandlerError("BadRequest: param is not a secret string parameter")

        created_at = datetime.datetime.now()
        created_at_str = (
            created_at.strftime("%Y-%m-%dT%H:%M:%S")
            + "."
            + created_at.strftime("%f")[0:3]  # milliseconds
            + "Z"
        )

        step.secrets = {
            **step.secrets,
            param: {"name": created_at_str, "secret": secret},
        }
        step.save(update_fields=["secrets"])

        return clientside.Update(
            steps={step.id: clientside.StepUpdate(secrets=step.secret_metadata)}
        )


@register_websockets_handler
@websockets_handler("owner")
@_loading_step_by_id
async def set_secret(workflow: Workflow, step: Step, param: str, secret: str, **kwargs):
    """Set a secret value `secret` on param `param`.

    `param` must point to a `secret` parameter with
    `secret_logic.provider == 'string'`. The server will set the `name` to
    the ISO8601-formatted representation of the current time, if `secret` is
    set to something new.
    """
    # Be safe with types
    param = str(param)
    secret = str(secret)
    update = await _step_set_secret_and_build_delta(workflow, step, param, secret)

    if update:
        await rabbitmq.send_update_to_workflow_clients(workflow.id, update)


@database_sync_to_async
def _do_set_file_upload_api_token(step: Step, api_token: Optional[str]):
    step.file_upload_api_token = api_token
    step.save(update_fields=["file_upload_api_token"])


@register_websockets_handler
@websockets_handler("write")
@_loading_step_by_slug
async def get_file_upload_api_token(workflow: Workflow, step: Step, **kwargs):
    """Query the file-upload API token.

    We do not pass this token in Deltas, since only writers can see it. (As of
    [2019-08-05], Deltas aren't tailored to individual listeners' permissions.)
    """
    return {"apiToken": step.file_upload_api_token}


@register_websockets_handler
@websockets_handler("write")
@_loading_step_by_slug
async def reset_file_upload_api_token(workflow: Workflow, step: Step, **kwargs):
    api_token = secrets.token_urlsafe()
    await _do_set_file_upload_api_token(step, api_token)
    return {"apiToken": api_token}


@register_websockets_handler
@websockets_handler("write")
@_loading_step_by_slug
async def clear_file_upload_api_token(workflow: Workflow, step: Step, **kwargs):
    await _do_set_file_upload_api_token(step, None)
