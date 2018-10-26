from server import websockets
from server import rabbitmq


# Trigger update on client side
async def notify_client_workflow_version_changed(workflow):
    await websockets.ws_client_rerender_workflow_async(workflow)
