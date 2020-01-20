# Receive and send websockets messages.
# Clients open a socket on a specific workflow, and all clients viewing that
# workflow are a "group"
from collections import namedtuple
import json
import logging
import pickle
from typing import Dict, Any
from channels.layers import get_channel_layer
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.exceptions import DenyConnection
from cjworkbench.sync import database_sync_to_async
from cjwstate import clientside, rabbitmq
from cjwstate.models import WfModule, Workflow
from server import handlers
from server.serializers import JsonizeContext, jsonize_clientside_update

logger = logging.getLogger(__name__)
WorkflowUpdateData = namedtuple("WorkflowUpdateData", ("update", "delta_id"))


def _workflow_group_name(workflow_id: int) -> str:
    """
    Build a channel_layer group name, given a workflow ID.

    Messages sent to this group will be sent to all clients connected to
    this workflow.
    """
    return f"workflow-{str(workflow_id)}"


@database_sync_to_async
def _get_workflow_as_clientside_update(
    user, session, workflow_id: int
) -> WorkflowUpdateData:
    """
    Return (clientside.Update, delta_id).

    Raise Workflow.DoesNotExist if a race deletes the Workflow.

    The purpose of this method is to hide races from users who disconnect
    and reconnect while changes are being made. It's okay for things to be
    slightly off, as long as users don't notice. (Long-term, we can build
    better a more-correct synchronization strategy.)
    """
    with Workflow.authorized_lookup_and_cooperative_lock(
        "read", user, session, pk=workflow_id
    ) as workflow_lock:
        workflow = workflow_lock.workflow
        update = clientside.Update(
            workflow=workflow.to_clientside(),
            tabs={tab.slug: tab.to_clientside() for tab in workflow.live_tabs},
            steps={
                step.id: step.to_clientside()
                for step in WfModule.live_in_workflow(workflow)
            },
        )
        return WorkflowUpdateData(update, workflow.last_delta_id)


class WorkflowConsumer(AsyncJsonWebsocketConsumer):
    @property
    def workflow_id(self):
        return int(self.scope["url_route"]["kwargs"]["workflow_id"])

    @property
    def workflow_channel_name(self):
        return _workflow_group_name(self.workflow_id)

    def get_workflow_sync(self):
        """The current user's Workflow, if exists and authorized; else None"""
        try:
            ret = Workflow.objects.get(pk=self.workflow_id)
        except Workflow.DoesNotExist:
            return None

        if not ret.user_session_authorized_read(
            self.scope["user"], self.scope["session"]
        ):
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
                level, self.scope["user"], self.scope["session"], pk=self.workflow_id
            ):
                return True
        except Workflow.DoesNotExist:
            return False

    async def connect(self):
        if not await self.authorize("read"):
            raise DenyConnection()

        await self.channel_layer.group_add(
            self.workflow_channel_name, self.channel_name
        )
        logger.debug("Added to channel %s", self.workflow_channel_name)
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
        # Double up log messages: one before, one after.
        # [2019-06-13] there's an error on production when a user has a flaky
        # Internet connection: "... took too long to shut down and was killed".
        # According to https://github.com/django/channels/issues/1119, this
        # method is to blame.
        #
        # Our problem is: a frontend server simply stops sending anything over
        # Websockets. And if we see one message without the other in the logs,
        # that suggests there's a problem in the channel layer.
        logger.debug("Starting discard from channel %s", self.workflow_channel_name)
        await self.channel_layer.group_discard(
            self.workflow_channel_name, self.channel_name
        )
        logger.debug("Discarded from channel %s", self.workflow_channel_name)

    async def send_whole_workflow_to_client(self):
        try:
            update, delta_id = await _get_workflow_as_clientside_update(
                self.scope["user"], self.scope["session"], self.workflow_id
            )
        except Workflow.DoesNotExist:
            return

        await self.send_update(update)
        if any(
            step.render_result == clientside.Null
            or (step.render_result.delta_id != step.last_relevant_delta_id)
            for step in update.steps.values()
        ):
            # Solve a problem: what if, when the user reconnects, the
            # workflow isn't rendered?
            #
            # Usually, a render is happening. But sometimes not. Perhaps we
            # cleared the cache. Or perhaps we deployed a new version of
            # Workbench that doesn't use the same cache format -- making
            # every workflow's cache invalid. In those cases, we should
            # cause a render just by dint of a user reconnecting.
            workflow_id = update.workflow.id
            logger.debug("Queue render of Workflow %d v%d", workflow_id, delta_id)
            await rabbitmq.queue_render(workflow_id, delta_id)

    async def send_pickled_update(self, message: Dict[str, Any]) -> None:
        # It's a bit of a security concern that we use pickle to send
        # dataclasses, through RabbitMQ, as opposed to protobuf. It's also
        # inefficient and makes for races when deploying new versions. But
        # it's _so_ much less code!  Let's only add complexity if we detect
        # a problem.
        await self.send_update(pickle.loads(message["pickled_update"]))

    async def send_update(self, update: clientside.Update) -> None:
        logger.debug("Send update to Workflow %d", self.workflow_id)
        ctx = JsonizeContext(
            self.scope["user"], self.scope["session"], self.scope["locale_id"]
        )
        json_dict = jsonize_clientside_update(update, ctx)
        await self.send_json({"type": "apply-delta", "data": json_dict})

    async def queue_render(self, message):
        """
        Request a render of `workflow_id` at delta `delta_id`

        A producer somewhere has requested, "please render, but only if
        somebody wants to see the render." Well, `self` is here representing a
        user who has the workflow open and wants to see the render.
        """
        delta_id = message["delta_id"]
        logger.debug("Queue render of Workflow %d v%d", self.workflow_id, delta_id)
        await rabbitmq.queue_render(self.workflow_id, delta_id)

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
                request_id = int(content["requestId"])
            except (KeyError, TypeError, ValueError):
                request_id = None

            return await self.send_json(
                {"response": {"requestId": request_id, "error": message}}
            )

        workflow = await self.get_workflow()  # and release lock
        if workflow is None:
            return await send_early_error("Workflow was deleted")

        try:
            request = handlers.HandlerRequest.parse_json_data(
                self.scope, workflow, content
            )
        except ValueError as err:
            return await send_early_error(str(err))

        logger.info("handlers.handle(%s, %s)", request.workflow.id, request.path)

        response = await handlers.handle(request)

        await self.send_json({"response": response.to_dict()})
