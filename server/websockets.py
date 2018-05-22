# Receive and send websockets messages.
# Clients open a socket on a specific workflow, and all clients viewing that workflow are a "group"
import json
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from channels.generic.websocket import JsonWebsocketConsumer
from channels.exceptions import DenyConnection
from typing import Dict, Any

def _workflow_channel_name(workflow_id: int) -> str:
    """Given a workflow ID, returns a channel_layer channel name.

    Messages sent to this channel name will be sent to all clients connected to
    this workflow.
    """
    return f"workflow-{str(workflow_id)}"

class WorkflowConsumer(JsonWebsocketConsumer):
    @property
    def workflow_id(self):
        return int(self.scope['url_route']['kwargs']['workflow_id'])

    @property
    def workflow_channel_name(self):
        return _workflow_channel_name(self.workflow_id)

    @property
    def workflow(self):
        """The current user's Workflow, if exists and authorized; else None
        """
        from server.models import Workflow

        try:
            ret = Workflow.objects.get(pk=self.workflow_id)
        except Workflow.DoesNotExist:
            return None

        if not ret.user_authorized_read(self.scope['user']):
            # failed auth. Don't leak any info: behave exactly as we would if
            # the workflow didn't exist
            return None

        return ret

    def connect(self):
        if self.workflow is None: raise DenyConnection()

        async_to_sync(self.channel_layer.group_add)(self.workflow_channel_name,
                                                    self.channel_name)
        self.accept()

    def disconnect(self):
        async_to_sync(self.channel_layer.group_discard)(self.workflow_channel_name,
                                                        self.channel_name)

    def send_data_to_workflow_client(self, message):
        self.send_json(message['data'])

def _workflow_group_send(workflow_id: int, message_dict: Dict[str,Any]) -> None:
    """Sends message_dict as JSON to all clients connected to the workflow.
    """
    channel_name = _workflow_channel_name(workflow_id)
    channel_layer = get_channel_layer()
    group_send = async_to_sync(channel_layer.group_send)
    group_send(channel_name, {
        'type': 'send_data_to_workflow_client',
        'data': message_dict,
    })

def ws_client_rerender_workflow(workflow) -> None:
    """Tells clients of the workflow to re-request it and update themselves.
    """
    message = { 'type': 'reload-workflow'}
    _workflow_group_send(workflow.id, message)

def ws_client_wf_module_status(wf_module, status):
    """Tells clients of the wf_module's workflow to reload the wf_module.
    """
    workflow = wf_module.workflow
    if workflow is None:
        # [adamhooper, 2018-05-22] when does this happen?
        return

    message = { 'type' : 'wfmodule-status', 'id' : wf_module.id, 'status' : status}
    _workflow_group_send(workflow.id, message)
