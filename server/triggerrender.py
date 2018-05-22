from server import websockets

# Trigger update on client side
def notify_client_workflow_version_changed(workflow):
    websockets.ws_client_rerender_workflow(workflow)
