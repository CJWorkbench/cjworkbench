import os
from cjworkbench import rabbitmq
from cjworkbench.pg_render_locker import PgRenderLocker
from .render import handle_render


# NRenderers: number of renders to perform simultaneously. This should be 1 per
# CPU, because rendering is CPU-bound. (It uses a fair amount of RAM, too.)
#
# Default is 1: we expect to run on a 2-CPU machine, so 1 CPU for render and 1
# for cron-render.
NRenderers = int(os.getenv('CJW_N_RENDERERS', 1))


async def main_loop():
    """
    Run fetchers and renderers, forever.
    """
    async with PgRenderLocker() as pg_render_locker:
        @rabbitmq.manual_acking_callback
        async def render_callback(message, ack):
            return await handle_render(message, ack, pg_render_locker)

        connection = rabbitmq.get_connection()
        connection.declare_queue_consume(
            rabbitmq.Render,
            NRenderers,
            render_callback
        )
        # Run forever
        await connection._closed_event.wait()
