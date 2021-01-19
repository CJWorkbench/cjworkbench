import asyncio
import logging

from django.core.management.base import BaseCommand

from cron.main import main as main_loop


logger = logging.getLogger(__name__)


def exit_on_exception(loop, context):
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
    help = "Loop: delete expired anonymous workflows and schedule fetches"

    def handle(self, *args, **options):
        asyncio.run(main())
