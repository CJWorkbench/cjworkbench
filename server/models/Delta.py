# Delta
# A single change to state of a workflow
# You can also think of this as a "command." Contains a specification of what actually happened.

from django.db import models
from server.models.Workflow import *
from django.db import transaction

# Base class of a single undoable/redoable action
# Derived classes implement the actual mutations on the database
# To derive a command from Delta:
class Delta(models.Model):

    # These fields must be set by any child classes, when instantiating that class
    workflow = models.ForeignKey('Workflow', related_name='deltas', on_delete=models.CASCADE)  # delete if Workflow deleted
    command_description = models.CharField('command_description', max_length=200)    # User-readable string

    # Next and previous Deltas on this workflow, a doubly linked list
    # Use related_name = '+' to indicate we don't want back links (we already have them!)
    next_delta = models.ForeignKey('self', related_name='+', null=True)
    prev_delta = models.ForeignKey('self', related_name='+', null=True)
    datetime = models.DateTimeField('datetime', auto_now=True)

    # On very first save, add this Delta to the linked list
    def save(self, *args, **kwargs):
        if not self.pk:
            # Brand new object, add at the end of the Delta linked list
            # Do this in a transaction, since we need to update three pointers to maintain list integrity
            with transaction.atomic():

                # Point us backward to last delta in chain
                last_delta = self.workflow.last_delta
                if last_delta:
                    self.prev_delta = last_delta

                # Save ourselves to DB, then point last delta to us
                super(Delta, self).save(*args, **kwargs)
                if last_delta:
                    last_delta.next_delta = self  # must be done after save, because we need our new pk
                    last_delta.save()

                # Point workflow to us
                self.workflow.last_delta = self
                self.workflow.save()
        else:
            # we're already in the linked list, just save
            super(Delta, self).save(*args, **kwargs)


    def __str__(self):
        return str(self.datetime) + " " + self.command_description

