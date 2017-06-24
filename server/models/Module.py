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

    def __str__(self):
        return self.name
