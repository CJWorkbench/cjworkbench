import functools
from typing import Any, Dict
from channels.db import database_sync_to_async
from server.models import Workflow, WfModule
from server.models.commands import ChangeParametersCommand, DeleteModuleCommand
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
