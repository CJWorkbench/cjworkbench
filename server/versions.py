# Revision tracking and client notification methods

from server.websockets import *
from django.utils import timezone

# --- Increment version, notify client of changes ---

def next_workflow_version(workflow):
    return workflow.revision + 1

def bump_workflow_version(workflow, notify_client=True):
    workflow.revision = next_workflow_version(workflow)
    workflow.revision_date = timezone.now()
    workflow.save()
    if notify_client:
        ws_client_rerender_workflow(workflow)


