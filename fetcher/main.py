import asyncio

import msgpack


async def main():
    """Fetch, forever."""
    # import AFTER django.setup()
    import cjwstate.modules
    from cjwstate import rabbitmq
    from cjwstate.rabbitmq.connection import open_global_connection
    from .fetch import handle_fetch

    cjwstate.modules.init_module_system()

    async with open_global_connection() as rabbitmq_connection:
        await rabbitmq_connection.queue_declare(rabbitmq.Fetch, durable=True)
        await rabbitmq_connection.queue_declare(rabbitmq.Render, durable=True)
        await rabbitmq_connection.exchange_declare(rabbitmq.GroupsExchange)
        # Fetch; ack; fetch; ack ... forever.
        async with rabbitmq_connection.acking_consumer(rabbitmq.Fetch) as consumer:
            async for message_bytes in consumer:
                message = msgpack.unpackb(message_bytes)
                await handle_fetch(message)


if __name__ == "__main__":
    import django

    django.setup()
    asyncio.run(main())
