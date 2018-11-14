import asyncio
from django.core.management.base import BaseCommand
from server.cron import main


class Command(BaseCommand):
    help = 'Loop: delete expired anonymous workflows and schedule fetches'

    def handle(self, *args, **options):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(main())
        loop.close()
