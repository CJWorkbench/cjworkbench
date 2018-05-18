from django.core.management.base import BaseCommand, CommandError
import server.initmodules
from server.models import Module,ModuleVersion
from server.importmodulefromgithub import import_module_from_github

class Command(BaseCommand):
    help = 'Re-imports all modules which were imported from github'

    def handle(self, *args, **options):

        totes = 0
        external_modules = Module.objects.exclude(link__exact='')
        for m in external_modules:
            url = m.link
            print('Importing module %s from %s' % (m.name, url))

            try:
                import_module_from_github(url)
                totes += 1
            except Exception as e:
                print(str(e))

        print('Imported %d external modules' % totes)