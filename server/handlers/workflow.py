from .decorators import register_websockets_handler, websockets_handler
from server.models import Workflow
from server.models.commands import ChangeWorkflowTitleCommand
from server.versions import WorkflowRedo, WorkflowUndo


@register_websockets_handler
@websockets_handler('write')
async def undo(workflow: Workflow, **kwargs):
    await WorkflowUndo(workflow)


@register_websockets_handler
@websockets_handler('write')
async def redo(workflow: Workflow, **kwargs):
    await WorkflowRedo(workflow)


@register_websockets_handler
@websockets_handler('write')
async def set_name(workflow: Workflow, name: str, **kwargs):
    name = str(name)  # JSON input cannot cause error here
    await ChangeWorkflowTitleCommand.create(workflow=workflow, new_value=name)
