import asyncio

from cjwstate import rabbitmq
from cjworkbench.pg_render_locker import PgRenderLocker
from .render import handle_render


async def main_loop():
    """Run fetchers and renderers, forever."""
    async with PgRenderLocker() as pg_render_locker:

        @rabbitmq.acking_callback
        async def render_callback(message):
            await handle_render(message, pg_render_locker)
            # Possible errors: DatabaseError, InterfaceError. Explanations:
            #
            # 1. There's a bug in renderer.execute. This may leave the event
            # loop's executor thread's database connection in an inconsistent
            # state. [2018-11-06 saw this on production.] The best way to clear
            # up the leaked, broken connection is to die. (Our parent process
            # should restart us, and RabbitMQ will give the job to someone
            # else.)
            #
            # 2. The database connection died (e.g., Postgres went away). The
            # best way to clear up the leaked, broken connection is to die.
            # (Our parent process should restart us, and RabbitMQ will give the
            # job to someone else.)
            #
            # 3. PgRenderLocker's database connection died (e.g., Postgres went
            # away). We haven't seen this much in practice; so let's die and let
            # the parent process restart us.
            #
            # 4. There's some design flaw we haven't thought of, and we
            # shouldn't ever render this workflow. If this is the case, we're
            # doomed.
            #
            # If you're seeing an error that means there's a bug somewhere
            # _else_. If you're staring at a case-3 situation, please remember
            # that cases 1 and 2 are important, too.

        connection = rabbitmq.get_connection()
        connection.declare_queue_consume(rabbitmq.Render, render_callback)
        await connection.wait_closed()
