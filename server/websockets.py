# Receive and send websockets messages.
# Clients open a socket on a specific workflow, and all clients viewing that
# workflow are a "group"
import logging
from typing import Dict, Any
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.exceptions import DenyConnection


logger = logging.getLogger(__name__)


def _workflow_channel_name(workflow_id: int) -> str:
    """Given a workflow ID, return a channel_layer channel name.

    Messages sent to this channel name will be sent to all clients connected to
    this workflow.
    """
    return f"workflow-{str(workflow_id)}"


class WorkflowConsumer(AsyncJsonWebsocketConsumer):
    @property
    def workflow_id(self):
        return int(self.scope['url_route']['kwargs']['workflow_id'])

    @property
    def workflow_channel_name(self):
        return _workflow_channel_name(self.workflow_id)

    @database_sync_to_async
    def get_workflow(self):
        """The current user's Workflow, if exists and authorized; else None
        """
        # [adamhooper, 2018-05-24] This should probably be async.
        from server.models import Workflow

        try:
            ret = Workflow.objects.get(pk=self.workflow_id)
        except Workflow.DoesNotExist:
            return None

        if not ret.user_session_authorized_read(self.scope['user'],
                                                self.scope['session']):
            # failed auth. Don't leak any info: behave exactly as we would if
            # the workflow didn't exist
            return None

        return ret

    async def connect(self):
        if await self.get_workflow() is None:
            raise DenyConnection()

        await self.channel_layer.group_add(self.workflow_channel_name,
                                           self.channel_name)
        logging.debug('Added to channel %s', self.workflow_channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.workflow_channel_name,
                                               self.channel_name)
        logging.debug('Discarded from channel %s', self.workflow_channel_name)

    async def send_data_to_workflow_client(self, message):
        logging.debug('Send %s to Workflow %d', message['data']['type'],
                      self.workflow_id)
        await self.send_json(message['data'])


async def _workflow_group_send(workflow_id: int,
                               message_dict: Dict[str, Any]) -> None:
    """Send message_dict as JSON to all clients connected to the workflow."""
    channel_name = _workflow_channel_name(workflow_id)
    channel_layer = get_channel_layer()
    logging.debug('Queue %s to Workflow %d', message_dict['type'],
                  workflow_id)
    await channel_layer.group_send(channel_name, {
        'type': 'send_data_to_workflow_client',
        'data': message_dict,
    })


async def ws_client_rerender_workflow_async(workflow) -> None:
    """Tell clients of the workflow to re-request it and update themselves."""
    message = {'type': 'reload-workflow'}
    await _workflow_group_send(workflow.id, message)


async def ws_client_send_delta_async(workflow_id: int,
                                     delta: Dict[str, Any]) -> None:
    """Tell clients how to modify their `workflow` and `wfModules` state."""
    message = {'type': 'apply-delta', 'data': delta}
    await _workflow_group_send(workflow_id, message)


async def ws_client_wf_module_status_async(wf_module, status):
    """Tell clients of the wf_module's workflow to reload the wf_module.
    """
    workflow = wf_module.workflow
    if workflow is None:
        # [adamhooper, 2018-05-22] when does this happen?
        return

    message = {
        'type': 'wfmodule-status',
        'id': wf_module.id,
        'status': status
    }
    await _workflow_group_send(workflow.id, message)
