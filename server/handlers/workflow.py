from .decorators import register_websockets_handler, websockets_handler
from server.models import Workflow
from server.versions import WorkflowRedo, WorkflowUndo


@register_websockets_handler
@websockets_handler('write')
async def undo(workflow: Workflow, **kwargs):
    await WorkflowUndo(workflow)


@register_websockets_handler
@websockets_handler('write')
async def redo(workflow: Workflow, **kwargs):
    await WorkflowRedo(workflow)
