from django.db import models
from django.contrib.auth.models import User

# A Workflow is the user's "document," a series of Modules
class Workflow(models.Model):
    name = models.CharField('name',max_length=200)
    creation_date = models.DateTimeField(auto_now_add=True)
    revision = models.IntegerField(default=1)
    revision_date = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    def user_authorized(self, user):
        return user == self.owner

    def __str__(self):
        return self.name

    def set_name(self, name):
        self.name = name
        return self.save()
