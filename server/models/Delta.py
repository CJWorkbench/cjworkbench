# Delta
# A single change to state of a workflow
# You can also think of this as a "command." Contains a specification of what actually happened.

from polymorphic.models import PolymorphicModel
from server.models.Workflow import *
from server.triggerrender import trigger_render
from django.db import transaction
import django.utils

# Base class of a single undoable/redoable action
# Derived classes implement the actual mutations on the database (via polymorphic forward()/backward())
# To derive a command from Delta:
#   - implement forward() and backward()
#   - implement a static create() that takes whatever parameters define the action,creates 
#     an instance of the Delta subclass with that info, sets the workflow and description,
#     and runs forward()
#
class Delta(PolymorphicModel):
    class Meta:
    # OMG this bug ate so many hours...
	# see https://github.com/django-polymorphic/django-polymorphic/issues/229
        base_manager_name = 'base_objects'

    # These fields must be set by any child classes, when instantiating that class
    workflow = models.ForeignKey('Workflow', related_name='deltas', on_delete=models.CASCADE)  # delete if Workflow deleted
    command_description = models.CharField('command_description', max_length=200)    # User-readable string

    # Next and previous Deltas on this workflow, a doubly linked list
    # Use related_name = '+' to indicate we don't want back links (we already have them!)
    next_delta = models.ForeignKey('self', related_name='+', null=True, default=None, on_delete=models.SET_DEFAULT)
    prev_delta = models.ForeignKey('self', related_name='+', null=True, default=None, on_delete=models.SET_DEFAULT)
    datetime = models.DateTimeField('datetime', default=django.utils.timezone.now)

    # On very first save, add this Delta to the linked list
    def save(self, *args, **kwargs):
        if not self.pk:
            # Brand new object, add at the end of the Delta linked list
            # Do this in a transaction, since we need to update three pointers to maintain list integrity
            with transaction.atomic():

                # Blow away all deltas starting after last applied (wipe redo stack)
                delete_unapplied_deltas(self.workflow)

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

        # workflow version bumped, re-render
        if self.triggers_rerender():
            trigger_render(self.workflow, self.rerender_from())


    # should this command, when applied, cause a re-render? Most commands do,
    # but some do not (e.g. change module update settings)
    def triggers_rerender(self):
        return True

    # Does this command apply to a particular module? Defining this in child classes
    # prevents previous modules from being re-rendered. None = re-render all
    def rerender_from(self):
        return None

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
