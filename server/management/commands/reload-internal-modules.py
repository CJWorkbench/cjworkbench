from django.core.management.base import BaseCommand
import server.initmodules


class Command(BaseCommand):
    help = 'Reloads all modules which are in the main server repo'

    def handle(self, *args, **options):
        server.initmodules.init_modules()
