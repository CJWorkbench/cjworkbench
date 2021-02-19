import asyncio
import logging
import os
import signal

import cjwstate.modules
from cjworkbench.sync import database_sync_to_async
from cjwstate.models.module_registry import MODULE_REGISTRY
from cjwstate.rabbitmq.connection import (
    maintain_global_connection,
    stop_global_connection,
)


logger = logging.getLogger(__name__)


async def _create_rabbitmq_maintainer() -> asyncio.Task:
    """Create a "connected" Future and a Task that maintains that connection.

    To use:

        try:
            task = await _create_rabbitmq_maintainer()
        except Exception:
            # Crash during startup! Startup failed

        # Now, `task` is running on the event loop and it will send us
        # `SIGTERM` if RabbitMQ disconnects and won't reconnect.
        #
        # ... for shutdown:
        await cjwstate.rabbitmq.connection.stop_global_connection()
        try:
            await task  # normal shutdown
        except Exception:
            # Crash during shutdown
    """
    connected_once: asyncio.Future[None] = asyncio.Future()

    async def on_connect(connection):
        await connection.exchange_declare("groups")
        await connection.queue_declare("render")
        await connection.queue_declare("fetch")
        connected_once.set_result(None)

    async def maintainer():
        try:
            await maintain_global_connection(on_connect=on_connect)
        except Exception as err:
            if not connected_once.done():
                # Error during startup: we're done
                connected_once.set_exception(err)
            else:
                # Error _after_ startup: shut us down!
                os.kill(os.getpid(), signal.SIGTERM)

    task = asyncio.create_task(maintainer())
    try:
        await connected_once
    except Exception:
        await task  # it already completed
        raise

    return task


class LifespanMiddleware:
    """Connect to RabbitMQ on startup; disconnect on shutdown."""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope["type"] != "lifespan":
            return await self.inner(scope, receive, send)

        task: Optional[asyncio.Task] = None

        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                try:
                    task = await _create_rabbitmq_maintainer()
                except Exception as err:
                    logger.exception("Error connecting to RabbitMQ")
                    await send({"type": "lifespan.startup.failed", "message": str(err)})
                    return

                try:
                    cjwstate.modules.init_module_system()
                except Exception as err:
                    logger.exception("Error initializing kernel")
                    await send({"type": "lifespan.startup.failed", "message": str(err)})
                    return

                try:
                    # Load static modules on startup.
                    #
                    # This means starting a kernel and validating all static modules.
                    # Good reasons to load during startup:
                    #
                    # 1. In dev mode, this reports errors in modules ASAP.
                    # 2. In production, this warms up our cache so the first requests
                    #    won't be served too slowly.
                    await database_sync_to_async(MODULE_REGISTRY.all_latest)()
                except Exception as err:
                    logger.exception("Error initializing modules")
                    await send({"type": "lifespan.startup.failed", "message": str(err)})
                    return

                await send({"type": "lifespan.startup.complete"})
                return
            elif message["type"] == "lifespan.shutdown":
                await stop_global_connection()

                try:
                    await self._task
                except Exception as err:
                    logger.exception("Error disconnecting from RabbitMQ")
                    await send(
                        {"type": "lifespan.shutdown.failed", "message": str(err)}
                    )
                    return
                await send({"type": "lifespan.shutdown.complete"})
                return
