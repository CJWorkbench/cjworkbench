import asyncio
import logging
import os
from django.core.management.base import BaseCommand
from ...main import main_loop


logger = logging.getLogger(__name__)


def exit_on_exception(loop, context):
    if "client_session" in context or "connector" in context or "transport" in context:
        # [2018-11-07] aiohttp raises spurious exceptions.
        # https://github.com/aio-libs/aiohttp/issues/2039
        #
        # For now, let's ignore any error from aiohttp. In the future, aiohttp
        # should fix its bug #2039, and then we can nix this comment and
        # handler.
        #
        # Exceptions we see:
        #
        # * context: {'connector': <...>, 'connections': ['[(...)]'],
        #             'message': 'Unclosed connector'}
        # * context: {'client_session': <...>,
        #             'message': 'Unclosed client session'}
        # * context: {'transport': <...>,
        #             'message': 'SSL handshake failed...'}
        logger.warn("Ignoring warning from aiohttp: %s", context["message"])
        return

    logger.error(
        "Exiting because of unhandled error: %s\nContext: %r",
        context["message"],
        context,
        exc_info=context.get("exception"),
    )
    os._exit(1)


async def main():
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(exit_on_exception)
    await main_loop()


class Command(BaseCommand):
    help = "Continually run cron- and user-initiated fetches."

    def handle(self, *args, **options):
        asyncio.run(main())
