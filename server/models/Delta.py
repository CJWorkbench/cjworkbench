# Delta
# A single change to state of a workflow
# You can also think of this as a "command." Contains a specification of what
# actually happened.
import json
from typing import Any, Dict
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
import django.utils
from polymorphic.models import PolymorphicModel
from server import websockets
from server.serializers import WorkflowSerializer, WfModuleSerializer


def _prepare_json(data: Any) -> Any:
    """Convert `data` into a simple, JSON-ready dict."""
    return json.loads(json.dumps(data, cls=DjangoJSONEncoder))


# Base class of a single undoable/redoable action
# Derived classes implement the actual mutations on the database
# (via polymorphic forward()/backward())
# To derive a command from Delta:
#   - implement forward_impl() and backward_impl()
#   - implement a static create() that takes parameters and calls
#     `Delta.create_impl(MyCommandClass, **kwargs)`. `Delta.create_impl()`
#     will call `delta.forward()` within a Workflow.cooperative_lock().
class Delta(PolymorphicModel):
    class Meta:
        # OMG this bug ate so many hours...
        # https://github.com/django-polymorphic/django-polymorphic/issues/229
        base_manager_name = 'base_objects'

    # These fields must be set by any child classes, when instantiating
    workflow = models.ForeignKey('Workflow', related_name='deltas',
                                 on_delete=models.CASCADE)
    command_description = models.CharField('command_description',
                                           max_length=200)  # User-readable str

    # Next and previous Deltas on this workflow, a doubly linked list
    # Use related_name = '+' to indicate we don't want back links (we already
    # have them!)
    next_delta = models.ForeignKey('self', related_name='+', null=True,
                                   default=None, on_delete=models.SET_DEFAULT)
    prev_delta = models.ForeignKey('self', related_name='+', null=True,
                                   default=None, on_delete=models.SET_DEFAULT)
    datetime = models.DateTimeField('datetime',
                                    default=django.utils.timezone.now)

    def forward(self):
        """Call forward_impl() with workflow.cooperative_lock()."""
        with self.workflow.cooperative_lock():
            self.forward_impl()
        self.ws_notify()

    def backward(self):
        """Call backward_impl() with workflow.cooperative_lock()."""
        with self.workflow.cooperative_lock():
            self.backward_impl()
        self.ws_notify()

    def ws_notify(self):
        """
        Notify WebSocket clients that we just undid or redid.

        This default implementation sends a 'delta' command. It will always
        include a 'set-workflow' property; it may include a 'set-wf-module'
        command and may include a 'clear-wf-module' command.
        """
        data = {}

        with self.workflow.cooperative_lock():
            workflow_data = WorkflowSerializer(self.workflow).data
            # Remove the data we didn't generate correctly because we had no
            # HTTP request.
            del workflow_data['is_anonymous']
            del workflow_data['owner_name']
            del workflow_data['read_only']
            data['updateWorkflow'] = _prepare_json(workflow_data)
            data['updateWfModules'] = {}

            if hasattr(self, '_changed_wf_module_versions'):
                for id, delta_id in self._changed_wf_module_versions.items():
                    data['updateWfModules'][str(id)] = {
                        'last_relevant_delta_id': delta_id,
                        'error_msg': '',
                        'output_columns': None
                    }

            if hasattr(self, 'wf_module'):
                self.wf_module.refresh_from_db()
                if self.wf_module.workflow_id:
                    wf_module_data = WfModuleSerializer(self.wf_module).data

                    data['updateWfModules'][str(self.wf_module_id)] = \
                        _prepare_json(wf_module_data)
                else:
                    # When we did or undid this command, we removed the
                    # WfModule from the Workflow.
                    data['clearWfModuleIds'] = [self.wf_module_id]

        websockets.ws_client_send_delta_sync(self.workflow_id, data)

    @staticmethod
    def create_impl(klass, **kwargs) -> None:
        """Create the given Delta and run .forward(), in a Workflow.cooperative_lock().

        Keyword arguments vary by klass, but `workflow` is always required.

        Example:

            delta = Delta.create_impl(ChangeWfModuleNotesCommand,
                workflow=wf_module.workflow,
                # ... other kwargs
            )
            # now delta has been applied and committed to the database.
        """
        workflow = kwargs['workflow']
        with workflow.cooperative_lock():
            delta = klass.objects.create(**kwargs)
            delta.forward()

        return delta

    def save(self, *args, **kwargs):
        # We only get here from create_impl(), forward_impl() and
        # backward_impl(). So we already hold self.workflow.cooperative_lock().
        if not self.pk:
            # On very first save, add this Delta to the linked list
            # The workflow lock is important here: we need to update three
            # pointers to maintain list integrity

            # wipe redo stack: blow away all deltas starting after last applied
            delete_unapplied_deltas(self.workflow)

            # Point us backward to last delta in chain
            last_delta = self.workflow.last_delta
            if last_delta:
                self.prev_delta = last_delta

            # Save ourselves to DB, then point last delta to us
            super(Delta, self).save(*args, **kwargs)
            if last_delta:
                last_delta.next_delta = self  # after save: we need our new pk
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
    # ensure last_delta is up to date after whatever else has been done to this
    # poor workflow
    workflow.refresh_from_db()

    # Starting pos is one after last_delta. Have to look in db if at start of
    # delta stack
    if workflow.last_delta:
        delta = workflow.last_delta.next_delta
    else:
        delta = Delta.objects \
                .filter(workflow=workflow) \
                .order_by('datetime') \
                .first()

    while delta:
        next = delta.next_delta
        delta.delete()
        delta = next
