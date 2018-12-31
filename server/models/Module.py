# A Module defines a data processing action, with a set of paramters
# Module is the class, WfModule is the instance (applied in a Workflow)
from django.db import models


class Module(models.Model):
    class Meta:
        ordering = ['name']

    # UI name, can change
    name = models.CharField('name', max_length=200)

    # Where it appears in menus and UI, can change
    category = models.CharField('category', max_length=200)

    # internal name, cannot change if you want backwards compatibility with exported workflows
    id_name = models.CharField('id_name', max_length=200)

    # how do we run this module?
    dispatch = models.CharField('dispatch', max_length=200)

    # where has this module come from? The default is "internal", i.e. it's a core module.
    source = models.CharField('source', max_length=200, default="internal")

    # the description of the module
    description = models.CharField('description', max_length=200, default="")

    # the author of the given module
    author = models.CharField('author', max_length=200, default="Workbench")

    # the url of the module repo
    link = models.URLField('link', max_length=200, default="")

    # icon name associated with module
    icon = models.CharField('icon', max_length=20, default='url')

    # Does this model bring in external data?
    loads_data = models.BooleanField('loads_data', default=False)

    # Can the user zoom to just this module for distraction-free editing?
    has_zen_mode = models.BooleanField('has_zen_mode', default=False)

    # URL for the module's documentation, defaults to our knowledge base root
    help_url = models.CharField('help_url', max_length=200, default="")

    # If set, add a row-selection menu option to create a module with its
    # `rows` parameter set to the selected rows in string form
    row_action_menu_entry_title = models.CharField(
        'row_action_menu_entry_title',
        max_length=200, default=''
    )

    # JavaScript to embed. It can set `module.exports`.
    js_module = models.TextField('js_module', default='')

    def __str__(self):
        return self.id_name
