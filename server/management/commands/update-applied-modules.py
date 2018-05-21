from django.core.management.base import BaseCommand
from server.initmodules import update_wfm_parameters_to_new_version
from server.models import WfModule,ModuleVersion

class Command(BaseCommand):
    help = 'Updates all modules in every workflow to latest imported version '

    def handle(self, *args, **options):
        totes=0
        for wfm in WfModule.objects.all():

            # update module if not missing and not internal
            if wfm.module_version != None and wfm.module_version.module.link != '':
                latest_version = ModuleVersion.objects.filter(module=wfm.module_version.module).order_by('-last_update_time').first()
                if wfm.module_version != latest_version:
                    print('Updating module %s from %s to %s' %
                          (str(wfm), wfm.module_version.source_version_hash, latest_version.source_version_hash))
                    update_wfm_parameters_to_new_version(wfm, latest_version)
                    totes += 1

        print('Updated %d applied modules to latest version' % totes)




