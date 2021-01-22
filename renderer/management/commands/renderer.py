import asyncio
import logging
import os
from django.core.management.base import BaseCommand
import cjwstate.modules
from ...main import main_loop


logger = logging.getLogger(__name__)


def exit_on_exception(loop, context):
    logger.error(
        "Exiting because of unhandled error: %s\nContext: %r",
        context["message"],
        context,
        exc_info=context.get("exception"),
    )
    logging.shutdown()
    os._exit(1)


async def main():
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(exit_on_exception)
    await main_loop()


class Command(BaseCommand):
    help = "Continually render stale workflows"

    def handle(self, *args, **options):
        cjwstate.modules.init_module_system()
        asyncio.run(main())
