from django.db import models
from django.contrib.auth.models import User

# A Workflow is the user's "document," a series of Modules
class Workflow(models.Model):
    name = models.CharField('name',max_length=200)
    creation_date = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    last_delta = models.ForeignKey('server.Delta',                # specify as string to avoid circular import
                                   related_name='+',              # + means no backward link
                                   null=True)   # if null, no Commands applied yet

    def user_authorized(self, user):
        return user == self.owner

    # use last delta ID as (non sequential) revision number, as later deltas will always have later ids
    def revision(self):
        if not self.last_delta:
            return 0
        else:
            return self.last_delta.id

    def __str__(self):
        return self.name

