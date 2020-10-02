from typing import List
from .decorators import register_websockets_handler, websockets_handler
from .types import HandlerError
from cjworkbench.sync import database_sync_to_async
from cjwstate import commands
from cjwstate.models import Tab, Workflow, Step
from cjwstate.models.commands import ChangeWorkflowTitleCommand, ReorderTabsCommand
from server.versions import WorkflowRedo, WorkflowUndo


@register_websockets_handler
@websockets_handler("write")
async def undo(workflow: Workflow, **kwargs):
    await WorkflowUndo(workflow.id)


@register_websockets_handler
@websockets_handler("write")
async def redo(workflow: Workflow, **kwargs):
    await WorkflowRedo(workflow.id)


@register_websockets_handler
@websockets_handler("write")
async def set_name(workflow: Workflow, name: str, **kwargs):
    name = str(name)  # JSON input cannot cause error here
    await commands.do(
        ChangeWorkflowTitleCommand, workflow_id=workflow.id, new_value=name
    )


@database_sync_to_async
def _write_step_position(workflow: Workflow, step_id: int) -> None:
    """Write position in DB, or raise (Workflow|Tab|Step).DoesNotExist."""
    with workflow.cooperative_lock():  # raises Workflow.DoesNotExist
        # Raises Step.DoesNotExist, e.g. if tab.is_deleted
        step = Step.live_in_workflow(workflow).get(pk=step_id)
        tab = step.tab

        tab.selected_step_position = step.order
        tab.save(update_fields=["selected_step_position"])

        workflow.selected_tab_position = tab.position
        workflow.save(update_fields=["selected_tab_position"])


@register_websockets_handler
@websockets_handler("write")
async def set_position(workflow: Workflow, stepId: int, **kwargs):
    if not isinstance(stepId, int):
        raise HandlerError("stepId must be a Number")

    try:
        await _write_step_position(workflow, stepId)
    except Step.DoesNotExist:
        # users are racing, or the request is otherwise invalid.
        # The information the user sent is hardly important. Ignore it,
        # rather than report an error nobody cares about.
        pass
    except Workflow.DoesNotExist:
        raise HandlerError("Workflow not found")


@database_sync_to_async
def _write_tab_position(workflow: Workflow, tab_slug: str) -> None:
    """Write position in DB, or raise (Workflow|Tab).DoesNotExist."""
    with workflow.cooperative_lock():  # raises Workflow.DoesNotExist
        # raises Tab.DoesNotExist, e.g. if tab.is_deleted
        tab = workflow.live_tabs.get(slug=tab_slug)

        workflow.selected_tab_position = tab.position
        workflow.save(update_fields=["selected_tab_position"])


@register_websockets_handler
@websockets_handler("write")
async def set_selected_tab(workflow: Workflow, tabSlug: str, **kwargs):
    tabSlug = str(tabSlug)  # cannot raise anything

    try:
        await _write_tab_position(workflow, tabSlug)
    except (Workflow.DoesNotExist, Tab.DoesNotExist):
        raise HandlerError("Invalid tab slug")


@register_websockets_handler
@websockets_handler("write")
async def set_tab_order(workflow: Workflow, tabSlugs: List[str], **kwargs):
    if not isinstance(tabSlugs, list):
        raise HandlerError("tabSlugs must be an Array of slugs")
    for tab_id in tabSlugs:
        if not isinstance(tab_id, str):
            raise HandlerError("tabSlugs must be an Array of slugs")

    try:
        await commands.do(
            ReorderTabsCommand, workflow_id=workflow.id, new_order=tabSlugs
        )
    except ValueError as err:
        if str(err) == "wrong tab slugs":
            raise HandlerError("wrong tab slugs")
        else:
            raise
