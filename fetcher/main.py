import asyncio

from django.conf import settings

from cjwstate import rabbitmq
from .fetch import handle_fetch


async def main_loop():
    """Fetch, forever."""
    connection = rabbitmq.get_connection()
    connection.declare_queue_consume(
        rabbitmq.Fetch, rabbitmq.acking_callback(handle_fetch)
    )
    await connection.wait_closed()
