import asyncio

import msgpack


async def main():
    """Run fetchers and renderers, forever."""
    # import AFTER django.setup()
    import cjwstate.modules
    from cjworkbench.pg_render_locker import PgRenderLocker
    from cjwstate import rabbitmq
    from cjwstate.rabbitmq.connection import open_global_connection
    from .render import handle_render

    cjwstate.modules.init_module_system()

    async with PgRenderLocker() as pg_render_locker, open_global_connection() as rabbitmq_connection:
        await rabbitmq_connection.queue_declare(rabbitmq.Render, durable=True)
        await rabbitmq_connection.exchange_declare(rabbitmq.GroupsExchange)
        # Render; ack; render; ack ... forever.
        async with rabbitmq_connection.acking_consumer(rabbitmq.Render) as consumer:
            async for message_bytes in consumer:
                message = msgpack.unpackb(message_bytes)
                # Crash on error, and don't ack.
                await handle_render(message, pg_render_locker)


if __name__ == "__main__":
    import django

    django.setup()
    asyncio.run(main())
