from typing import Any, Dict
from channels.db import database_sync_to_async
from server.models import Workflow, WfModule
from server.models.commands import ChangeParametersCommand
from .. import register_websockets_handler, websockets_handler


@database_sync_to_async
def _load_wf_module(workflow: Workflow, wf_module_id: int) -> WfModule:
    """Returns a WfModule or raises WfModule.DoesNotExist."""
    return workflow.wf_modules.get(id=wf_module_id)


def loading_wf_module(func):
    @functools.wraps(func)
    async def inner(workflow: Workflow, wf_module_id: int, **kwargs):
        wf_module = await _load_wf_module(workflow, wf_module_id)
        return await func(workflow=workflow, wf_module=wf_module, **kwargs)
    return inner


@register_websockets_handler
@loading_wf_module
@websockets_handler('write')
async def set_params(workflow: Workflow, wf_module: WfModule,
                     values: Dict[str, Any], **kwargs):
    await ChangeParametersCommand.create(workflow=workflow,
                                         wf_module=wf_module,
                                         new_values=values)
