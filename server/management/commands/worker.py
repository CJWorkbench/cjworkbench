import asyncio
import logging
from django.core.management.base import BaseCommand
from django.utils import autoreload
from server.worker import main_loop


logger = logging.getLogger(__name__)


def exit_on_exception(loop, context):
    import sys
    logger.error('Exiting because of unhandled exception: %s',
                 context['exception'])
    sys.exit(1)


def main():
    loop = asyncio.new_event_loop()
    loop.set_exception_handler(exit_on_exception)
    loop.create_task(main_loop())
    loop.run_forever()
    loop.close()


class Command(BaseCommand):
    help = 'Continually delete expired anonymous workflows and fetch wfmodules'

    def handle(self, *args, **options):
        autoreload.main(main)
