from django.db import models
from server.dispatch import module_dispatch

# A Workflow is the user's "document," a series of Modules
class Workflow(models.Model):
    name = models.CharField('name',max_length=200)
    creation_date = models.DateTimeField(auto_now_add=True)
    revision = models.IntegerField(default=1)
    revision_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
