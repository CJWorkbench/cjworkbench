from django.core.management.base import BaseCommand
from server.initmodules import update_wfm_parameters_to_new_version
from server.models import WfModule,ModuleVersion

class Command(BaseCommand):
    help = 'Updates all modules in every workflow to latest imported version '

    def handle(self, *args, **options):
        totes=0
        for wfm in WfModule.objects.all():
            module = wfm.module_version.module

            if module != None:      # could be a missing module
                latest_version = ModuleVersion.objects.filter(module=module).order_by('-last_update_time').first()
                if wfm.module_version != latest_version:
                    update_wfm_parameters_to_new_version(wfm, latest_version)
                    totes += 1

        print('Updated %d applied modules to latest version' % totes)


