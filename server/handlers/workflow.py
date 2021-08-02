from typing import List
from .decorators import register_websockets_handler, websockets_handler
from .types import HandlerError
from cjworkbench.sync import database_sync_to_async
from cjwstate import commands, rabbitmq
from cjwstate.models import Tab, Workflow, Step
from cjwstate.models.commands import SetWorkflowTitle, ReorderTabs


@register_websockets_handler
@websockets_handler("write")
async def undo(workflow: Workflow, **kwargs):
    await commands.undo(workflow.id)


@register_websockets_handler
@websockets_handler("write")
async def redo(workflow: Workflow, **kwargs):
    await commands.redo(workflow.id)


@register_websockets_handler
@websockets_handler("write")
async def set_name(workflow: Workflow, name: str, **kwargs):
    name = str(name)  # JSON input cannot cause error here
    await commands.do(SetWorkflowTitle, workflow_id=workflow.id, new_value=name)


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


@database_sync_to_async
def _get_tab_slugs_for_dataset(workflow: Workflow) -> List[str]:
    return list(
        workflow.live_tabs.filter(is_in_dataset=True).values_list("slug", flat=True)
    )


@register_websockets_handler
@websockets_handler("owner")
async def begin_publish_dataset(
    workflow: Workflow, requestId: str, workflowUpdatedAt: str, **kwargs
):
    if str(workflowUpdatedAt) != workflow.updated_at.isoformat() + "Z":
        raise HandlerError("updated-at-mismatch")

    await rabbitmq.queue_render(
        workflow.id,
        workflow.last_delta_id,
        rabbitmq.PublishDatasetSpec(
            request_id=str(requestId),
            workflow_name=workflow.name,
            readme_md=workflow.dataset_readme_md,
            tab_slugs=await _get_tab_slugs_for_dataset(workflow),
        ),
    )


@register_websockets_handler
@websockets_handler("write")
async def set_tab_order(workflow: Workflow, tabSlugs: List[str], **kwargs):
    if not isinstance(tabSlugs, list):
        raise HandlerError("tabSlugs must be an Array of slugs")
    for tab_id in tabSlugs:
        if not isinstance(tab_id, str):
            raise HandlerError("tabSlugs must be an Array of slugs")

    try:
        await commands.do(ReorderTabs, workflow_id=workflow.id, new_order=tabSlugs)
    except ValueError as err:
        if str(err) == "wrong tab slugs":
            raise HandlerError("wrong tab slugs")
        else:
            raise
