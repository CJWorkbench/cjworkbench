# Delta
# A single change to state of a workflow
# You can also think of this as a "command." Contains a specification of what actually happened.

from django.db import models
from server.models.Workflow import *

# Base class of a single undoable/redoable action
# Derived classes implement the actual mutations on the database
class Delta(models.Model):

    # Which workflow, and what revision of that workflow?
    workflow = models.ForeignKey(Workflow, related_name='deltas', on_delete=models.CASCADE)  # delete if Workflow deleted
    revision = models.IntegerField(default=1)  # after application of this delta
    datetime = models.DateTimeField('datetime', auto_now=True)

    # What happened? User-readable string
    command_description = models.CharField('command_description', max_length=200)

    def __str__(self):
        return str(self.datetime) + " " + self.command_description

