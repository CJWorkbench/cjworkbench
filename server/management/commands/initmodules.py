from django.core.management.base import BaseCommand, CommandError
import server.initmodules

class Command(BaseCommand):
    help = 'Copies Module metadata from disk to database'

    def handle(self, *args, **options):
        server.initmodules.init_modules()
