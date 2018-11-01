import asyncio
import time
from django.core.management.base import BaseCommand
from server.maintenance import delete_expired_anonymous_workflows
from server.updates import update_wfm_data_scan
from server.utils import get_console_logger
from server.worker import PgLocker


_logger = get_console_logger()


_MaxDelay = 60  # seconds


async def main():
    async with PgLocker() as pg_locker:
        while True:
            time1 = time.time()

            try:
                await update_wfm_data_scan(pg_locker)
            except Exception as err:
                _logger.exception(err)

            try:
                delete_expired_anonymous_workflows()
            except Exception as err:
                _logger.exception(err)

            time2 = time.time()
            duration = time2 - time1
            delay = max(0, _MaxDelay - duration)
            await asyncio.sleep(delay)


class Command(BaseCommand):
    help = 'Loop: delete expired anonymous workflows and schedule fetches'

    def handle(self, *args, **options):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(main())
        loop.close()
