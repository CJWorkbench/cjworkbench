import logging
import pickle
from collections import namedtuple
from typing import Any, ContextManager, Dict

from channels.exceptions import DenyConnection
from channels.generic.websocket import AsyncJsonWebsocketConsumer

import websockets
from cjworkbench.sync import database_sync_to_async
from cjwstate import clientside, rabbitmq
from cjwstate.models import Step, Workflow
from cjwstate.models.module_registry import MODULE_REGISTRY
from server import handlers
from server.serializers import JsonizeContext, jsonize_clientside_update

logger = logging.getLogger(__name__)
WorkflowUpdateData = namedtuple("WorkflowUpdateData", ("update", "delta_id"))


@database_sync_to_async
def _load_latest_modules():
    return dict(MODULE_REGISTRY.all_latest())


class WorkflowConsumer(AsyncJsonWebsocketConsumer):
    """Receive and send websockets messages.

    Clients open a socket on a specific workflow, and all clients viewing that
    workflow are a "group".
    """

    def _lookup_requested_workflow_with_auth_and_cooperative_lock(
        self,
    ) -> ContextManager[Workflow]:
        """Either yield the requested workflow, or raise Workflow.DoesNotExist

        Workflow.DoesNotExist means "permission denied" or "workflow does not exist".
        """
        workflow_id_or_secret_id = self.scope["url_route"]["kwargs"][
            "workflow_id_or_secret_id"
        ]
        if isinstance(workflow_id_or_secret_id, int):
            return Workflow.authorized_lookup_and_cooperative_lock(
                "read",
                self.scope["user"],
                self.scope["session"],
                id=workflow_id_or_secret_id,
            )  # raise Workflow.DoesNotExist
        else:
            return Workflow.lookup_and_cooperative_lock(
                secret_id=workflow_id_or_secret_id
            )  # raise Workflow.DoesNotExist

    @database_sync_to_async
    def _read_requested_workflow_with_auth(self):
        with self._lookup_requested_workflow_with_auth_and_cooperative_lock() as workflow:
            return workflow

    @database_sync_to_async
    def _get_workflow_as_clientside_update(self) -> WorkflowUpdateData:
        """Return (clientside.Update, delta_id).

        Raise Workflow.DoesNotExist if a race deletes the Workflow.
        """
        with self._lookup_requested_workflow_with_auth_and_cooperative_lock() as workflow:
            update = clientside.Update(
                workflow=workflow.to_clientside(),
                tabs={tab.slug: tab.to_clientside() for tab in workflow.live_tabs},
                steps={
                    step.id: step.to_clientside()
                    for step in Step.live_in_workflow(workflow)
                },
            )
            return WorkflowUpdateData(update, workflow.last_delta_id)

    async def connect(self):
        try:
            workflow = await self._read_requested_workflow_with_auth()
            self.workflow_id = workflow.id
        except Workflow.DoesNotExist:
            raise DenyConnection()  # not found, or not authorized

        self.workflow_channel_name = "workflow-%d" % self.workflow_id
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
        await self._send_whole_workflow_to_client()

    async def disconnect(self, code):
        if hasattr(self, "workflow_channel_name"):
            await self.channel_layer.group_discard(
                self.workflow_channel_name, self.channel_name
            )
            logger.debug("Discarded from channel %s", self.workflow_channel_name)

    async def _send_whole_workflow_to_client(self):
        try:
            update, delta_id = await self._get_workflow_as_clientside_update()
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
            logger.debug("Queue render of Workflow %d v%d", self.workflow_id, delta_id)
            await rabbitmq.queue_render(self.workflow_id, delta_id)

    async def send_pickled_update(self, message: Dict[str, Any]) -> None:
        # It's a bit ugly that we use pickle (as opposed to protobuf) to send
        # through RabbitMQ. It's also inefficient and makes races when deploying
        # new versions. And security-wise, we're vulnerable to "AMQP injection"
        # attacks (arbitrary code execution if someone controls RabbitMQ). But
        # it's _so_ much less code! So there we have it.
        await self.send_update(pickle.loads(message["pickled_update"]))

    async def send_update(self, update: clientside.Update) -> None:
        logger.debug("Send update to Workflow %d", self.workflow_id)
        module_zipfiles = await _load_latest_modules()
        ctx = JsonizeContext(
            locale_id=self.scope["locale_id"],
            module_zipfiles=module_zipfiles,
        )
        json_dict = jsonize_clientside_update(update, ctx)
        await self.send_json_ignoring_connection_closed(
            {"type": "apply-delta", "data": json_dict}
        )

    async def send_json_ignoring_connection_closed(self, message) -> None:
        """Call AsyncJsonWebsocketConsumer.send_json(message); ignore an error.

        The error in question, "websockets.exceptions.ConnectionClosed", happens
        when the user disconnects at just the wrong time: either by closing the
        browser window, or by dropping the TCP connection. (A closed connection
        leads to disconnect; this error error happens during a race. As of
        [2020-12-15], it's ~150 times per week.)

        Call this method instead of `send_json()` when it's okay for the message
        to be lost. This should be _all_ cases.
        """
        try:
            await self.send_json(message)
        except websockets.exceptions.ConnectionClosed as err:
            if (
                err.code == 1001  # "going away" - user closed browser tab
                or err.code == 1006  # "connection closed abnormally"
            ):
                # We're sending an update, but the user's browser isn't
                # connected any more. This is not a problem.
                logger.debug(
                    "Websocket disconnected before we could send, for Workflow %d",
                    self.workflow_id,
                )
            else:
                # Undefined behavior. [2020-12-15] we've never seen this.
                raise

    async def queue_render(self, message):
        """Request a render of `workflow_id` at delta `delta_id`

        A producer somewhere has requested, "please render, but only if
        somebody wants to see the render." Well, `self` is here representing a
        user who has the workflow open and wants to see the render.
        """
        delta_id = message["delta_id"]
        logger.debug("Queue render of Workflow %d v%d", self.workflow_id, delta_id)
        await rabbitmq.queue_render(self.workflow_id, delta_id)

    async def receive_json(self, content):
        """Handle a query from the client."""

        async def send_early_error(message):
            """Respond that the request is invalid.

            Sometimes we won't be able to figure out requestId; we'll pass
            `null` in that case.
            """
            try:
                request_id = int(content["requestId"])
            except (KeyError, TypeError, ValueError):
                request_id = None

            return await self.send_json_ignoring_connection_closed(
                {"response": {"requestId": request_id, "error": message}}
            )

        try:
            # TODO nix this check (and adjust every handler to match). This
            # code only turns a race into a smaller race. Handlers still need
            # to handle the possibility that the workflow was deleted. (They
            # skip the auth as of [2021-03-25], though.)
            #
            # Maybe we should pass
            # `self._lookup_requested_workflow_with_auth_and_cooperative_lock`
            # as a callback?
            workflow = await self._read_requested_workflow_with_auth()
        except Workflow.DoesNotExist:
            return await send_early_error("Workflow was deleted")

        try:
            request = handlers.HandlerRequest.parse_json_data(
                self.scope, workflow, content
            )
        except ValueError as err:
            return await send_early_error(str(err))

        logger.info("handlers.handle(%s, %s)", request.workflow.id, request.path)

        response = await handlers.handle(request)

        await self.send_json_ignoring_connection_closed(
            {"response": response.to_dict()}
        )
