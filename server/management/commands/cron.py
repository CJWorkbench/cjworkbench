import asyncio
from django.core.management.base import BaseCommand
from server.cron import main


class Command(BaseCommand):
    help = 'Loop: delete expired anonymous workflows and schedule fetches'

    def handle(self, *args, **options):
        asyncio.run(main())
