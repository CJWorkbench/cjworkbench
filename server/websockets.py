# Receive and send websockets messages.
# Clients open a socket on a specific workflow, and all clients viewing that
# workflow are a "group"
from collections import namedtuple
import json
import logging
from typing import Dict, Any
from django.core.serializers.json import DjangoJSONEncoder
from channels.layers import get_channel_layer
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.exceptions import DenyConnection
from cjworkbench.sync import database_sync_to_async
from server import handlers, rabbitmq
from server.models import WfModule, Workflow
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
    # Override Channels JSON-dumping to support datetime
    @classmethod
    async def encode_json(cls, data: Any) -> str:
        return json.dumps(data, cls=DjangoJSONEncoder)

    @property
    def workflow_id(self):
        return int(self.scope['url_route']['kwargs']['workflow_id'])

    @property
    def workflow_channel_name(self):
        return _workflow_channel_name(self.workflow_id)

    def get_workflow_sync(self):
        """The current user's Workflow, if exists and authorized; else None"""
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
        try:
            with Workflow.authorized_lookup_and_cooperative_lock(
                level,
                self.scope['user'],
                self.scope['session'],
                pk=self.workflow_id
            ):
                return True
        except Workflow.DoesNotExist:
            return False

    @database_sync_to_async
    def get_workflow_as_delta_and_needs_render(self):
        """
        Return (apply-delta dict, needs_render), or raise Workflow.DoesNotExist

        needs_render is a (workflow_id, delta_id) pair.
        """
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
                                       context={'request': request}).data
                ),
            }

            tabs = list(workflow.live_tabs)
            ret['updateTabs'] = dict((tab.slug, TabSerializer(tab).data)
                                     for tab in tabs)
            wf_modules = list(WfModule.live_in_workflow(workflow.id))
            ret['updateWfModules'] = dict((str(wfm.id),
                                           WfModuleSerializer(wfm).data)
                                          for wfm in wf_modules)

            if workflow.are_all_render_results_fresh():
                needs_render = None
            else:
                needs_render = (workflow.id, workflow.last_delta_id)

            return (ret, needs_render)

    async def connect(self):
        if not await self.authorize('read'):
            raise DenyConnection()

        await self.channel_layer.group_add(self.workflow_channel_name,
                                           self.channel_name)
        logger.debug('Added to channel %s', self.workflow_channel_name)
        await self.accept()

        # Solve a race:
        #
        # 1. User loads a workflow that isn't rendered, triggering render
        # 2. Server sends "busy" workflow
        # 3. Render completes
        # 4. User connects over Websockets
        #
        # Expected results: user sees completed render
        await self.send_whole_workflow_to_client()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.workflow_channel_name,
                                               self.channel_name)
        logger.debug('Discarded from channel %s', self.workflow_channel_name)

    async def send_whole_workflow_to_client(self):
        try:
            delta, needs_render = \
                    await self.get_workflow_as_delta_and_needs_render()
            await self.send_data_to_workflow_client({
                'data': {  # TODO why the nesting?
                    'type': 'apply-delta',
                    'data': delta,
                }
            })
            if needs_render:
                # Solve a problem: what if, when the user reconnects, the
                # workflow isn't rendered?
                #
                # Usually, a render is happening. But sometimes not. Perhaps we
                # cleared the cache. Or perhaps we deployed a new version of
                # Workbench that doesn't use the same cache format -- making
                # every workflow's cache invalid. In those cases, we should
                # cause a render just by dint of a user reconnecting.
                workflow_id, delta_id = needs_render
                logger.debug('Queue render of Workflow %d v%d',
                             workflow_id, delta_id)
                await rabbitmq.queue_render(workflow_id, delta_id)
        except Workflow.DoesNotExist:
            pass

    async def send_data_to_workflow_client(self, message):
        logger.debug('Send %s to Workflow %d', message['data']['type'],
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
        logger.debug('Queue render of Workflow %d v%d', workflow_id, delta_id)
        await rabbitmq.queue_render(workflow_id, delta_id)

    async def receive_json(self, content):
        """
        Handle a query from the client.
        """
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
            request = handlers.HandlerRequest.parse_json_data(self.scope,
                                                              workflow,
                                                              content)
        except ValueError as err:
            return await send_early_error(str(err))

        logger.info('handlers.handle(%s, %s)', request.workflow.id,
                    request.path)

        response = await handlers.handle(request)

        await self.send_json({'response': response.to_dict()})


async def _workflow_group_send(workflow_id: int,
                               message_dict: Dict[str, Any]) -> None:
    """Send message_dict as JSON to all clients connected to the workflow."""
    channel_name = _workflow_channel_name(workflow_id)
    channel_layer = get_channel_layer()
    logger.debug('Queue %s to Workflow %d', message_dict['type'],
                 workflow_id)
    await channel_layer.group_send(channel_name, {
        'type': 'send_data_to_workflow_client',
        'data': message_dict,
    })


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
    logger.debug('Suggest render of Workflow %d v%d', workflow_id, delta_id)
    await channel_layer.group_send(channel_name, {
        'type': 'queue_render',
        'data': {
            'workflow_id': workflow_id,
            'delta_id': delta_id,
        }
    })
