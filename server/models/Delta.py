# Delta
# A single change to state of a workflow
# You can also think of this as a "command." Contains a specification of what actually happened.

from polymorphic.models import PolymorphicModel
from server.models.Workflow import *
from django.db import transaction

# Base class of a single undoable/redoable action
# Derived classes implement the actual mutations on the database (via polymorphic forward()/backward())
# To derive a command from Delta:
#   - implement forward() and backward()
#   - implement a static create() that takes whatever parameters define the action,
#     creates an instance of the Delta subclass with tht info, and runs forward()
#
class Delta(PolymorphicModel):

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

                # Blow away all deltas starting after last applied (wipe redo stack)
                # delete_unapplied_deltas(self.workflow) ## Temporarily commenting out until we figure out what's going on with integrity errors

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


# Deletes every delta on the workflow that is not currently applied
# This is what implements undo + make a change -> can't redo
def delete_unapplied_deltas(workflow):

    # ensure last_delta is up to date after whatever else has been done to this poor workflow
    workflow.refresh_from_db()

    # Starting pos is one after last_delta. Have to look in db if at start of delta stack
    if workflow.last_delta:
        delta = workflow.last_delta.next_delta
    else:
        delta = Delta.objects.filter(workflow=workflow).order_by('datetime').first()

    while delta != None:
        next = delta.next_delta
        delta.delete()
        delta = next
