# ModuleVersion is a module that keeps track of the different versions of a single module, thereby allowing users to
# create workflows with different versions of the same module. This could be for a myriad of reasons, including
# backward compatibiity (not everyone's ready to use the latest version of a model), beta testing, etc.
#
# [adamhooper, 2018-12-27] ... and we support zero of those reasons.

from django.db import models


class ModuleVersion(models.Model):
    class Meta:
        ordering = ['last_update_time']

    # which version of this module are we currently at (based on the source)?
    source_version_hash = models.CharField('source_version_hash', max_length=200, default='1.0')

    # time this module was last updated
    last_update_time = models.DateTimeField('last_update_time', null=True, auto_now_add=True) #null for the core (read internal) modules.

    module = models.ForeignKey(
        'Module',
        related_name='module_versions',
        on_delete=models.CASCADE
    )

    # Does this module provide an html file for additional output?
    html_output = models.BooleanField('html_output', default=False)

    # Shortcut properties so we can duck-type ModuleVersion and make it look
    # exactly like a Module.
    #
    # Really, this is inverted: `Module` should have no properties (or, heck,
    # not exist at all). `ModuleVersion` is the only user-visible thing.
    @property
    def name(self):
        return self.module.name

    @property
    def category(self):
        return self.module.category

    @property
    def id_name(self):
        return self.module.id_name

    @property
    def dispatch(self):
        return self.module.dispatch

    @property
    def source(self):
        return self.module.source

    @property
    def description(self):
        return self.module.description

    @property
    def author(self):
        return self.module.author

    @property
    def link(self):
        return self.module.link

    @property
    def icon(self):
        return self.module.icon

    @property
    def loads_data(self):
        return self.module.loads_data

    @property
    def has_zen_mode(self):
        return self.module.has_zen_mode

    @property
    def help_url(self):
        return self.module.help_url

    @property
    def row_action_menu_entry_title(self):
        return self.module.row_action_menu_entry_title

    @property
    def js_module(self):
        return self.module.js_module

    def __str__(self):
        return self.module.name + ":" + self.source_version_hash
