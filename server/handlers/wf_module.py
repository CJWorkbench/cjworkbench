import datetime
import functools
from typing import Any, Dict
from channels.db import database_sync_to_async
from dateutil.parser import isoparse
from server.models import Workflow, WfModule
from server.models.commands import ChangeParametersCommand, \
        DeleteModuleCommand, ChangeDataVersionCommand
from .types import HandlerError
from .decorators import register_websockets_handler, websockets_handler


@database_sync_to_async
def _load_wf_module(workflow: Workflow, wf_module_id: int) -> WfModule:
    """Returns a WfModule or raises HandlerError."""
    try:
        return WfModule.live_in_workflow(workflow).get(id=wf_module_id)
    except WfModule.DoesNotExist:
        raise HandlerError('DoesNotExist: WfModule not found')


def loading_wf_module(func):
    @functools.wraps(func)
    async def inner(workflow: Workflow, wfModuleId: int, **kwargs):
        wf_module = await _load_wf_module(workflow, wfModuleId)
        return await func(workflow=workflow, wf_module=wf_module, **kwargs)
    return inner


@register_websockets_handler
@websockets_handler('write')
@loading_wf_module
async def set_params(workflow: Workflow, wf_module: WfModule,
                     values: Dict[str, Any], **kwargs):
    if not isinstance(values, dict):
        raise HandlerError('BadRequest: values must be an Object')

    await ChangeParametersCommand.create(workflow=workflow,
                                         wf_module=wf_module,
                                         new_values=values)


@register_websockets_handler
@websockets_handler('write')
@loading_wf_module
async def delete(workflow: Workflow, wf_module: WfModule, **kwargs):
    await DeleteModuleCommand.create(workflow=workflow, wf_module=wf_module)


@database_sync_to_async
def find_precise_version(wf_module: WfModule,
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
    except:
        return version

@database_sync_to_async
def mark_stored_object_read(wf_module: WfModule,
                            version: datetime.datetime) -> None:
    wf_module.stored_objects.filter(stored_at=version).update(read=True)

@register_websockets_handler
@websockets_handler('write')
@loading_wf_module
async def set_stored_data_version(workflow: Workflow, wf_module: WfModule,
                                  version: str, **kwargs):
    try:
        # cast to str: dateutil.parser may have vulnerability with non-str
        version = str(version)
        version = isoparse(version)
    except (ValueError, OverflowError, TypeError):
        raise HandlerError('BadRequest: version must be an ISO8601 datetime')

    version = await find_precise_version(wf_module, version)

    await ChangeDataVersionCommand.create(workflow=workflow,
                                          wf_module=wf_module,
                                          new_version=version)

    await mark_stored_object_read(wf_module, version)
