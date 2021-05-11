import functools
import re
from typing import Any, Dict, List
from cjworkbench.sync import database_sync_to_async
from cjwstate import commands
from cjwstate.models import Workflow, Tab
from cjwstate.models.module_registry import MODULE_REGISTRY
from cjwstate.models.commands import (
    AddStep,
    AddTab,
    DeleteTab,
    DuplicateTab,
    ReorderSteps,
    SetTabName,
)
from cjwstate.modules.types import ModuleZipfile
from .types import HandlerError
from .decorators import register_websockets_handler, websockets_handler
import server.utils


@database_sync_to_async
def _load_tab(workflow: Workflow, tab_slug: int) -> Tab:
    """Returns a Step or raises HandlerError."""
    try:
        return workflow.live_tabs.get(slug=tab_slug)
    except Tab.DoesNotExist:
        raise HandlerError("DoesNotExist: Tab not found")


@database_sync_to_async
def _load_module_zipfile(module_id_name: str) -> ModuleZipfile:
    """Return a ModuleZipfile or raise HandlerError."""
    try:
        return MODULE_REGISTRY.latest(module_id_name)
    except KeyError:
        raise HandlerError("KeyError: ModuleVersion not found")


def _loading_tab(func):
    @functools.wraps(func)
    async def inner(workflow: Workflow, tabSlug: str, **kwargs):
        tabSlug = str(tabSlug)  # never raises anything
        tab = await _load_tab(workflow, tabSlug)
        return await func(workflow=workflow, tab=tab, **kwargs)

    return inner


SlugRegex = re.compile(r"\A[-a-zA-Z0-9_]+\Z")


def _parse_slug(slug: str):
    """Return `slug` or raise ValueError."""
    slug = str(slug)  # cannot error from JSON params
    if not SlugRegex.match(slug):
        raise HandlerError(
            f'BadRequest: slug must match regex "[-a-zA-Z0-9_]+"; got "{slug}"'
        )
    return slug


@register_websockets_handler
@websockets_handler("write")
@_loading_tab
async def add_module(
    scope,
    workflow: Workflow,
    tab: Tab,
    slug: str,
    moduleIdName: str,
    position: int,
    paramValues: Dict[str, Any],
    **kwargs,
):
    slug = _parse_slug(slug)

    if not isinstance(paramValues, dict):
        raise HandlerError("BadRequest: paramValues must be an Object")

    if not isinstance(position, int):
        raise HandlerError("BadRequest: position must be a Number")

    moduleIdName = str(moduleIdName)

    # don't allow python code module in anonymous workflow
    if moduleIdName == "pythoncode" and workflow.is_anonymous:
        return None

    try:
        await commands.do(
            AddStep,
            workflow_id=workflow.id,
            tab=tab,
            slug=slug,
            module_id_name=moduleIdName,
            position=position,
            param_values=paramValues,
        )
    except KeyError:
        raise HandlerError("BadRequest: module does not exist")
    except ValueError as err:
        raise HandlerError("BadRequest: param validation failed: %s" % str(err))

    server.utils.log_user_event_from_scope(scope, f"ADD STEP {moduleIdName}")


@register_websockets_handler
@websockets_handler("write")
@_loading_tab
async def reorder_steps(
    workflow: Workflow, tab: Tab, slugs: List[str], mutationId: str, **kwargs
):
    if not isinstance(mutationId, str):
        raise HandlerError("BadRequest: mutationId must be String")
    if not isinstance(slugs, list):
        raise HandlerError('BadRequest: slugs must be an Array of "[-a-zA-Z0-9_]+"')
    slugs = [_parse_slug(slug) for slug in slugs]
    try:
        await commands.do(
            ReorderSteps,
            mutation_id=mutationId,
            workflow_id=workflow.id,
            tab=tab,
            slugs=slugs,
        )
    except ValueError as err:
        raise HandlerError(str(err))


@register_websockets_handler
@websockets_handler("write")
async def create(workflow: Workflow, slug: str, name: str, mutationId: str, **kwargs):
    if not isinstance(mutationId, str):
        raise HandlerError("BadRequest: mutationId must be String")
    slug = _parse_slug(slug)
    name = str(name)  # JSON values can't lead to error
    await commands.do(
        AddTab, mutation_id=mutationId, workflow_id=workflow.id, slug=slug, name=name
    )


@register_websockets_handler
@websockets_handler("write")
@_loading_tab
async def duplicate(
    workflow: Workflow, tab: Tab, slug: str, name: str, mutationId: str, **kwargs
):
    if not isinstance(mutationId, str):
        raise HandlerError("BadRequest: mutationId must be String")
    try:
        await commands.do(
            DuplicateTab,
            mutation_id=mutationId,
            workflow_id=workflow.id,
            from_tab=tab,
            slug=slug,
            name=name,
        )
    except ValueError as err:
        raise HandlerError("BadRequest: %s" % str(err))


@register_websockets_handler
@websockets_handler("write")
@_loading_tab
async def delete(workflow: Workflow, tab: Tab, mutationId: str, **kwargs):
    if not isinstance(mutationId, str):
        raise HandlerError("BadRequest: mutationId must be String")
    await commands.do(
        DeleteTab, workflow_id=workflow.id, tab=tab, mutation_id=mutationId
    )


@register_websockets_handler
@websockets_handler("write")
@_loading_tab
async def set_name(workflow: Workflow, tab: Tab, name: str, mutationId: str, **kwargs):
    if not isinstance(mutationId, str):
        raise HandlerError("BadRequest: mutationId must be String")
    name = str(name)  # JSON values can't lead to error
    await commands.do(
        SetTabName,
        workflow_id=workflow.id,
        tab=tab,
        new_name=name,
        mutation_id=mutationId,
    )
