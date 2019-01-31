import asyncio
import datetime
import functools
from typing import Any, Dict, Optional
from channels.db import database_sync_to_async
from dateutil.parser import isoparse
from django.conf import settings
from server import oauth, rabbitmq, websockets
from server.models import Params, Workflow, WfModule
from server.models.commands import ChangeParametersCommand, \
        DeleteModuleCommand, ChangeDataVersionCommand, \
        ChangeWfModuleNotesCommand
from .types import HandlerError
from .decorators import register_websockets_handler, websockets_handler


@database_sync_to_async
def _load_wf_module(workflow: Workflow, wf_module_id: int) -> WfModule:
    """Returns a WfModule or raises HandlerError."""
    try:
        return WfModule.live_in_workflow(workflow).get(id=wf_module_id)
    except WfModule.DoesNotExist:
        raise HandlerError('DoesNotExist: WfModule not found')


def _loading_wf_module(func):
    @functools.wraps(func)
    async def inner(workflow: Workflow, wfModuleId: int, **kwargs):
        wf_module = await _load_wf_module(workflow, wfModuleId)
        return await func(workflow=workflow, wf_module=wf_module, **kwargs)
    return inner


@register_websockets_handler
@websockets_handler('write')
@_loading_wf_module
async def set_params(workflow: Workflow, wf_module: WfModule,
                     values: Dict[str, Any], **kwargs):
    if not isinstance(values, dict):
        raise HandlerError('BadRequest: values must be an Object')

    try:
        await ChangeParametersCommand.create(workflow=workflow,
                                             wf_module=wf_module,
                                             new_values=values)
    except ValueError as err:
        raise HandlerError('ValueError: ' + str(err))


@register_websockets_handler
@websockets_handler('write')
@_loading_wf_module
async def delete(workflow: Workflow, wf_module: WfModule, **kwargs):
    await DeleteModuleCommand.create(workflow=workflow, wf_module=wf_module)


@database_sync_to_async
def _find_precise_version(wf_module: WfModule,
                          version: datetime.datetime) -> datetime.datetime:
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
            stored_at__lt=version + datetime.timedelta(milliseconds=1)
        ).values_list('stored_at', flat=True)[0]
    except IndexError:
        return version


@database_sync_to_async
def _mark_stored_object_read(wf_module: WfModule,
                             version: datetime.datetime) -> None:
    wf_module.stored_objects.filter(stored_at=version).update(read=True)


@register_websockets_handler
@websockets_handler('write')
@_loading_wf_module
async def set_stored_data_version(workflow: Workflow, wf_module: WfModule,
                                  version: str, **kwargs):
    try:
        # cast to str: dateutil.parser may have vulnerability with non-str
        version = str(version)
        version = isoparse(version)
    except (ValueError, OverflowError, TypeError):
        raise HandlerError('BadRequest: version must be an ISO8601 datetime')

    version = await _find_precise_version(wf_module, version)

    await ChangeDataVersionCommand.create(workflow=workflow,
                                          wf_module=wf_module,
                                          new_version=version)

    await _mark_stored_object_read(wf_module, version)


@register_websockets_handler
@websockets_handler('write')
@_loading_wf_module
async def set_notes(workflow: Workflow, wf_module: WfModule, notes: str,
                    **kwargs):
    notes = str(notes)  # cannot error from JSON input
    await ChangeWfModuleNotesCommand.create(workflow=workflow,
                                            wf_module=wf_module,
                                            new_value=notes)


@database_sync_to_async
def _set_collapsed_in_db(wf_module: WfModule, is_collapsed: bool) -> None:
    wf_module.is_collapsed = is_collapsed
    wf_module.save(update_fields=['is_collapsed'])


@register_websockets_handler
@websockets_handler('write')
@_loading_wf_module
async def set_collapsed(workflow: Workflow, wf_module: WfModule,
                        isCollapsed: bool, **kwargs):
    is_collapsed = bool(isCollapsed)  # cannot error from JSON input
    await _set_collapsed_in_db(wf_module, is_collapsed)


@database_sync_to_async
def _set_wf_module_busy(wf_module):
    wf_module.is_busy = True
    wf_module.save(update_fields=['is_busy'])


@register_websockets_handler
@websockets_handler('write')
@_loading_wf_module
async def fetch(workflow: Workflow, wf_module: WfModule, **kwargs):
    await _set_wf_module_busy(wf_module)
    await rabbitmq.queue_fetch(wf_module)
    await websockets.ws_client_send_delta_async(workflow.id, {
        'updateWfModules': {
            str(wf_module.id): {'is_busy': True, 'fetch_error': ''},
        }
    })


@register_websockets_handler
@websockets_handler('owner')
@_loading_wf_module
async def generate_secret_access_token(workflow: Workflow, wf_module: WfModule,
                                       param: str, **kwargs):
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
        offline_token = secrets[param]['secret']
    except TypeError:
        # secrets[param] is None
        return {'token': None}
    except KeyError:
        # There is no such secret param, or it is unset
        return {'token': None}
    except ValueError:
        # The param has the wrong type
        return {'token': None}
    if not offline_token:
        # Empty JSON -- no value has been set
        return {'token': None}

    service = oauth.OAuthService.lookup_or_none(param)
    if not service:
        allowed_services = settings.PARAMETER_OAUTH_SERVICES.keys()
        raise HandlerError(
            f'AuthError: we only support {", ".join(allowed_services)}'
        )

    # TODO make oauth async. In the meantime, move these HTTP requests to a
    # background thread.
    loop = asyncio.get_event_loop()
    func = functools.partial(service.generate_access_token_or_str_error,
                             offline_token)
    token = await loop.run_in_executor(None, func)
    if isinstance(token, str):
        raise HandlerError(f'AuthError: {token}')

    # token['access_token'] is short-term (1hr). token['refresh_token'] is
    # super-private and we should never transmit it.
    return {'token': token['access_token']}


@database_sync_to_async
def _wf_module_delete_secret_and_build_delta(
    workflow: Workflow,
    wf_module: WfModule,
    param: str
) -> Optional[Dict[str, Any]]:
    """
    Write a new secret (or `None`) to `wf_module`, or raise.

    Return a "delta" for websockets.ws_client_send_delta_async(), or `None` if
    the database has not been modified.

    Raise Workflow.DoesNotExist if the Workflow was deleted.
    """
    with workflow.cooperative_lock():  # raises Workflow.DoesNotExist
        wf_module.refresh_from_db()  # may return None

        if (
            wf_module is None
            or wf_module.secrets.get(param) is None
        ):
            return None

        wf_module.secrets = dict(wf_module.secrets)
        del wf_module.secrets[param]
        wf_module.save(update_fields=['secrets'])

        return {
            'updateWfModules': {
                str(wf_module.id): {
                    'params': wf_module.get_params().as_dict()
                }
            }
        }


@register_websockets_handler
@websockets_handler('owner')
@_loading_wf_module
async def delete_secret(workflow: Workflow, wf_module: WfModule, param: str,
                        **kwargs):
    delta = await _wf_module_delete_secret_and_build_delta(workflow, wf_module,
                                                           param)
    if delta:
        await websockets.ws_client_send_delta_async(workflow.id, delta)
