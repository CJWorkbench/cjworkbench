from cjwstate import rabbitmq
from cjworkbench.pg_render_locker import PgRenderLocker
from .render import handle_render


async def main_loop():
    """
    Run fetchers and renderers, forever.
    """
    async with PgRenderLocker() as pg_render_locker:

        @rabbitmq.manual_acking_callback
        async def render_callback(message, ack):
            return await handle_render(message, ack, pg_render_locker)

        connection = rabbitmq.get_connection()
        connection.declare_queue_consume(rabbitmq.Render, render_callback)
        # Run forever
        await connection._closed_event.wait()
