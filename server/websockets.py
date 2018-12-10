# Receive and send websockets messages.
# Clients open a socket on a specific workflow, and all clients viewing that
# workflow are a "group"
from collections import namedtuple
import logging
from typing import Dict, Any
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.exceptions import DenyConnection
from server import rabbitmq, handlers
from server.serializers import WorkflowSerializer, TabSerializer, \
        WfModuleSerializer

logger = logging.getLogger(__name__)
RequestWrapper = namedtuple('RequestWrapper', ('user', 'session'))


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

    def get_workflow_sync(self):
        """The current user's Workflow, if exists and authorized; else None"""
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

    @database_sync_to_async
    def get_workflow(self):
        """The current user's Workflow, if exists and authorized; else None"""
        return self.get_workflow_sync()

    @database_sync_to_async
    def authorize(self, level):
        from server.models import Workflow
        try:
            with Workflow.authorized_lookup_and_cooperative_lock(
                level,
                self.scope['user'],
                self.scope['session'],
                pk=self.workflow_id
            ) as workflow:
                return True
        except Workflow.DoesNotExist:
            return False

    @database_sync_to_async
    def get_workflow_as_delta(self):
        """Return an apply-delta dict, or raise Workflow.DoesNotExist."""
        from server.models import Workflow

        with Workflow.authorized_lookup_and_cooperative_lock(
            'read',
            self.scope['user'],
            self.scope['session'],
            pk=self.workflow_id
        ) as workflow:
            request = RequestWrapper(self.scope['user'],
                                     self.scope['session'])
            ret = {
                'updateWorkflow': (
                    WorkflowSerializer(workflow,
                                       context={'request': request})
                ),
            }

            tabs = list(workflow.live_tabs)
            ret['updateTabs'] = dict((str(tab.id), TabSerializer(tab).data)
                                     for tab in tabs)
            tab_ids = [tab.id for tab in tabs]
            wf_modules = list(WfModule.live_in_workflow(workflow.id))
            ret['updateWfModules'] = dict((str(wfm.id),
                                           WfModuleSerializer(wfm).data)
                                          for wfm in wf_modules)

            return ret

    async def connect(self):
        if not await self.authorize('read'):
            raise DenyConnection()

        await self.channel_layer.group_add(self.workflow_channel_name,
                                           self.channel_name)
        logging.debug('Added to channel %s', self.workflow_channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.workflow_channel_name,
                                               self.channel_name)
        logging.debug('Discarded from channel %s', self.workflow_channel_name)

    async def send_whole_workflow_to_client(self):
        from server.models import Workflow

        try:
            delta = await self.get_workflow_as_delta()
            await self.send_data_to_workflow_client({
                'type': 'apply-delta',
                'data': delta,
            })
        except Workflow.DoesNotExist:
            pass

    async def send_data_to_workflow_client(self, message):
        logging.debug('Send %s to Workflow %d', message['data']['type'],
                      self.workflow_id)
        await self.send_json(message['data'])

    async def queue_render(self, message):
        """
        Request a render of `workflow_id` at delta `delta_id`

        A producer somewhere has requested, "please render, but only if
        somebody wants to see the render." Well, `self` is here representing a
        user who has the workflow open and wants to see the render.
        """
        data = message['data']
        workflow_id = data['workflow_id']
        delta_id = data['delta_id']
        logging.debug('Queue render of Workflow %d v%d', workflow_id, delta_id)
        await rabbitmq.queue_render(workflow_id, delta_id)

    async def receive_json(self, content):
        """
        Handle a query from the client.
        """
        user = self.scope['user']
        session = self.scope['session']

        async def send_early_error(message):
            """
            Respond that the request is invalid.

            Sometimes we won't be able to figure out requestId; we'll pass
            `null` in that case.
            """
            try:
                request_id = int(content['requestId'])
            except (KeyError, TypeError, ValueError):
                request_id = None

            return await self.send_json({
                'response': {
                    'requestId': request_id,
                    'error': message
                }
            })

        workflow = await self.get_workflow()  # and release lock
        if workflow is None:
            return await send_early_error('Workflow was deleted')

        try:
            request = handlers.HandlerRequest.parse_json_data(user, session,
                                                              workflow,
                                                              content)
        except ValueError as err:
            return await send_early_error(str(err))

        response = await handlers.handle(request)

        await self.send_json({'response': response.to_dict()})


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


async def queue_render_if_listening(workflow_id: int, delta_id: int):
    """
    Tell workflow communicators to queue a render of `workflow`.

    In other words: "queue a render, but only if somebody has this workflow
    open in a web browser."
    """
    channel_name = _workflow_channel_name(workflow_id)
    channel_layer = get_channel_layer()
    logging.debug('Suggest render of Workflow %d v%d', workflow_id,
                  delta_id)
    await channel_layer.group_send(channel_name, {
        'type': 'queue_render',
        'data': {
            'workflow_id': workflow_id,
            'delta_id': delta_id,
        }
    })
