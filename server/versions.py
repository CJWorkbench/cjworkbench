# Undo, redo, and other version related things
from server.models import Delta, Workflow
from server.websockets import *

# Undo is pretty much just running workflow.last_delta backwards
def WorkflowUndo(workflow):
    delta = workflow.last_delta

    # Undo, if not at the very beginning of undo chain
    if delta:
        delta.backward()
        workflow.refresh_from_db() # backward() may change it
        workflow.last_delta = delta.prev_delta
        workflow.save()

        # oh, also update the version, and notify the client
        notify_client_workflow_version_changed(workflow)


# Redo is pretty much just running workflow.last_delta.next_delta forward
def WorkflowRedo(workflow):

    # if we are at very beginning of delta chain, find first delta from db
    if workflow.last_delta:
        next_delta = workflow.last_delta.next_delta
    else:
        next_delta = Delta.objects.filter(workflow=workflow).order_by('datetime').first()

    # Redo, if not at very end of undo chain
    if next_delta:
        next_delta.forward()
        workflow.refresh_from_db() # forward() may change it
        workflow.last_delta = next_delta
        workflow.save()

        # oh, also update the version, and notify the client
        notify_client_workflow_version_changed(workflow)


# Trigger re-render on client side
def notify_client_workflow_version_changed(workflow):
    ws_client_rerender_workflow(workflow)

