# Revision tracking and client notification methods

import server.models
from server.websockets import *
from django.utils import timezone

# --- Increment version, notify client of changes ---
def bump_workflow_version(workflow):
    workflow.revision += 1
    workflow.revision_date = timezone.now()
    workflow.save()
    ws_client_rerender_workflow(workflow)


