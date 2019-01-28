import functools
from typing import Any, Dict, List
from channels.db import database_sync_to_async
from server.models import ModuleVersion, Workflow, Tab
from server.models.commands import AddModuleCommand, ReorderModulesCommand, \
    AddTabCommand, DeleteTabCommand, SetTabNameCommand
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
def _load_module_version(module_id_name: str) -> Tab:
    """Returns a ModuleVersion or raises HandlerError."""
    try:
        return ModuleVersion.objects.latest(module_id_name)
    except ModuleVersion.DoesNotExist:
        raise HandlerError('DoesNotExist: ModuleVersion not found')


def _loading_tab(func):
    @functools.wraps(func)
    async def inner(workflow: Workflow, tabId: int, **kwargs):
        tab = await _load_tab(workflow, tabId)
        return await func(workflow=workflow, tab=tab, **kwargs)
    return inner


@register_websockets_handler
@websockets_handler('write')
@_loading_tab
async def add_module(scope, workflow: Workflow, tab: Tab, moduleIdName: str,
                     position: int, paramValues: Dict[str, Any], **kwargs):
    if not isinstance(paramValues, dict):
        raise HandlerError('BadRequest: paramValues must be an Object')

    if not isinstance(position, int):
        raise HandlerError('BadRequest: position must be a Number')

    moduleIdName = str(moduleIdName)

    # don't allow python code module in anonymous workflow
    if moduleIdName == 'pythoncode' and workflow.is_anonymous:
        return None

    try:
        await AddModuleCommand.create(workflow=workflow, tab=tab,
                                      module_id_name=moduleIdName,
                                      position=position,
                                      param_values=paramValues)
    except ModuleVersion.DoesNotExist:
        raise HandlerError('BadRequest: module does not exist')
    except ValueError as err:
        raise HandlerError('BadRequest: param validation failed: %s'
                           % str(err))

    # TODO switch Intercom around and log by moduleIdName, not module name
    # (Currently, we end up with two events every time we change names)
    module_version = await _load_module_version(moduleIdName)
    server.utils.log_user_event_from_scope(
        scope,
        f'ADD STEP {module_version.name}', {
            'name': module_version.name,
            'id_name': moduleIdName
        }
    )


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


@register_websockets_handler
@websockets_handler('write')
async def create(workflow: Workflow, slug: str, name: str, **kwargs):
    slug = str(slug)  # JSON values can't lead to error
    name = str(name)  # JSON values can't lead to error
    await AddTabCommand.create(workflow=workflow, slug=slug, name=name)


@register_websockets_handler
@websockets_handler('write')
@_loading_tab
async def delete(workflow: Workflow, tab: Tab, **kwargs):
    await DeleteTabCommand.create(workflow=workflow, tab=tab)


@register_websockets_handler
@websockets_handler('write')
@_loading_tab
async def set_name(workflow: Workflow, tab: Tab, name: str, **kwargs):
    name = str(name)  # JSON values can't lead to error
    await SetTabNameCommand.create(workflow=workflow, tab=tab, new_name=name)
