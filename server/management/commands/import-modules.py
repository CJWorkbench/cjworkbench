from django.core.management.base import BaseCommand
from server.importmodulefromgithub import import_module_from_github


class Command(BaseCommand):
    help = 'Reimport arguments from https://github.com/CJWorkbench/SLUG.git'

    def add_arguments(self, parser):
        parser.add_argument('slugs', nargs='+', type=str,
                            help='Name of GitHub repo')

    def handle(self, *args, slugs, **kwargs):
        for slug in slugs:
            import_module_from_github(
                'https://github.com/CJWorkbench/%s.git' % slug,
                force_reload=True
            )
