import datetime
from typing import List, Optional

from django.db.models import Case, When

from cjworkbench.sync import database_sync_to_async
from cjwstate import clientside, commands, rabbitmq
from cjwstate.models import Tab, Workflow, Step
from cjwstate.models.commands import SetWorkflowTitle, ReorderTabs
from .decorators import register_websockets_handler, websockets_handler
from .types import HandlerError


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


@database_sync_to_async
def _do_update_next_dataset(
    workflow: Workflow,
    readme_md: Optional[str] = None,
    include_tab_slugs: Optional[List[str]] = None,
) -> clientside.Update:
    with workflow.cooperative_lock():
        workflow.updated_at = datetime.datetime.now()
        workflow_fields = ["updated_at"]

        if readme_md is not None:
            workflow.dataset_readme_md = readme_md
            workflow_fields.append("dataset_readme_md")

        if include_tab_slugs is not None:
            # update all tabs (not just live ones). It's not obvious what should
            # happen with deleted tags; our arbitrary choice is to make it so we
            # try and save whatever the user sees.
            workflow.tabs.update(
                is_in_dataset=Case(
                    When(slug__in=include_tab_slugs, then=True), default=False
                )
            )

        workflow.save(update_fields=workflow_fields)
        return clientside.Update(
            workflow=clientside.WorkflowUpdate(
                updated_at=workflow.updated_at,
                next_dataset_readme_md=readme_md,  # or None
                next_dataset_tab_slugs=include_tab_slugs,  # or None
            )
        )


@register_websockets_handler
@websockets_handler("write")
async def update_next_dataset(
    workflow: Workflow,
    readmeMd: Optional[str] = None,
    tabSlugs: Optional[List[str]] = None,
    **kwargs,
):
    kwargs = {}

    if tabSlugs is not None:
        if not isinstance(tabSlugs, list):
            raise HandlerError("tabSlugs must be a list")
        kwargs["include_tab_slugs"] = [str(x) for x in tabSlugs]

    if readmeMd is not None:
        kwargs["readme_md"] = str(readmeMd)

    if not kwargs:
        raise HandlerError("BadRequest: must set readmeMd or tabSlugs")

    update = await _do_update_next_dataset(workflow, **kwargs)
    await rabbitmq.send_update_to_workflow_clients(workflow, update)


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
