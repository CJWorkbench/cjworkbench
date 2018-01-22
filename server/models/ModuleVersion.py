# ModuleVersion is a module that keeps track of the different versions of a single module, thereby allowing users to
# create workflows with different versions of the same module. This could be for a myriad of reasons, including
# backward compatibiity (not everyone's ready to use the latest version of a model), beta testing, etc.

from django.db import models

class ModuleVersion(models.Model):
    class Meta:
        ordering = ['last_update_time']

    # which version of this module are we currently at (based on the source)?
    source_version_hash = models.CharField('source_version_hash', max_length=200, default='1.0')

    # time this module was last updated
    last_update_time = models.DateTimeField('last_update_time', null=True, auto_now_add=True) #null for the core (read internal) modules.

    module = models.ForeignKey('Module', related_name='module_versions',
                                on_delete=models.CASCADE)  # nullifies when the corresponding module's deleted.

    # Does this module provide an html file for additional output?
    html_output = models.BooleanField('html_output', default=False)

    def __str__(self):
        return self.module.name + ":" + self.source_version_hash
