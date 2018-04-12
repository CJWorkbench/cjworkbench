from django.core.management.base import BaseCommand
from server.initmodules import load_module_from_file
from cjworkbench import settings
from os.path import join, isfile


class Command(BaseCommand):
    help = 'Reloads a specific module from the provided json file'

    def add_arguments(self, parser):
        parser.add_argument('filepath', nargs='?', type=str)

    def handle(self, *args, **options):
        path = join(settings.BASE_DIR, options['filepath'])

        if isfile(path):
            load_module_from_file(path)
            self.stdout.write(self.style.SUCCESS('Succesfully updated %s' % path))
        else:
            self.stdout.write(self.style.ERROR('%s does not appear to be a file' % path))
