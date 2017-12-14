from channels import Channel
from server.websockets import *
import sys

# kick off django channels background task. render_from = starting from this module down
def trigger_render(workflow, render_from):
    # we can't re-render on testing, because the ASGI channel layer fills up from the barrage of parallel tests,
    # even though individual tests work ok. Also, do we really want to spawn background tasks during testing?

    # Not turning this on yet
    #    if not sys.argv[1:2] == ['test']:
    #        Channel('execute-render').send({workflow: workflow, render_from: render_from})
    pass

# Trigger update on client side
def notify_client_workflow_version_changed(workflow):
    ws_client_rerender_workflow(workflow)