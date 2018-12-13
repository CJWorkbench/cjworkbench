import functools
from typing import Any, Dict, List
from channels.db import database_sync_to_async
from server.models import ModuleVersion, Workflow, Tab
from server.models.commands import AddModuleCommand, ReorderModulesCommand
from .types import HandlerError
from .decorators import register_websockets_handler, websockets_handler
import server.utils


@database_sync_to_async
def _load_tab(workflow: Workflow, tab_id: int) -> Tab:
    """Returns a WfModule or raises HandlerError."""
    try:
        return workflow.live_tabs.get(id=tab_id)
    except Tab.DoesNotExist:
        raise HandlerError('DoesNotExist: Tab not found')


@database_sync_to_async
def _load_module_version(module_id: int) -> Tab:
    """Returns a ModuleVersion or raises HandlerError."""
    module_version = (ModuleVersion.objects
                      .filter(module_id=module_id)
                      .order_by('-last_update_time')
                      .first())
    if module_version is None:
        raise HandlerError('DoesNotExist: ModuleVersion not found')
    else:
        return module_version


def _loading_tab(func):
    @functools.wraps(func)
    async def inner(workflow: Workflow, tabId: int, **kwargs):
        tab = await _load_tab(workflow, tabId)
        return await func(workflow=workflow, tab=tab, **kwargs)
    return inner


def _loading_module_version(func):
    @functools.wraps(func)
    async def inner(moduleId: int, **kwargs):
        module_version = await _load_module_version(moduleId)
        return await func(module_version=module_version, **kwargs)
    return inner


@register_websockets_handler
@websockets_handler('write')
@_loading_tab
@_loading_module_version
async def add_module(scope, workflow: Workflow, tab: Tab,
                     module_version: ModuleVersion,
                     position: int, paramValues: Dict[str, Any], **kwargs):
    if not isinstance(paramValues, dict):
        raise HandlerError('BadRequest: paramValues must be an Object')

    if not isinstance(position, int):
        raise HandlerError('BadRequest: position must be a Number')

    # don't allow python code module in anonymous workflow
    module = module_version.module
    if module.id_name == 'pythoncode' and workflow.is_anonymous:
        return None

    server.utils.log_user_event_from_scope(scope, f'ADD STEP {module.name}', {
        'name': module.name,
        'id_name': module.id_name
    })

    await AddModuleCommand.create(workflow=workflow, tab=tab,
                                  module_version=module_version,
                                  position=position,
                                  param_values=paramValues)


@register_websockets_handler
@websockets_handler('write')
@_loading_tab
async def reorder_modules(workflow: Workflow, tab: Tab,
                          wfModuleIds: List[int], **kwargs):
    try:
        await ReorderModulesCommand.create(workflow=workflow, tab=tab,
                                           new_order=wfModuleIds)
    except ValueError as err:
        raise HandlerError(str(err))
