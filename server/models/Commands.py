# A Command changes the state of a Workflow, by producing and executing a Delta

from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from server.models import WfModule, ParameterVal, Delta
import json
import logging
import threading

logger = logging.getLogger(__name__)

# --- Utilities ---

# Give the new WfModule an 'order' of insert_before, and add 1 to all following WfModules
def insert_wf_module(wf_module, workflow, insert_before):
    if insert_before < 0:
        insert_before = 0

    # This algorithm is deliberately robust to non-standard ordering (not 0..n-1)
    pos = 0
    for wfm in WfModule.objects.filter(workflow=workflow):
        if pos == insert_before:
            pos += 1
        if wfm.order != pos:
            wfm.order = pos
            wfm.save()
        pos += 1

    # normalize insert_before so it's always the index where the new WfModule ends up
    if insert_before > pos:
        insert_before = pos

    # save new position if needed
    if wf_module.order != insert_before:
        wf_module.order = insert_before

# Forces canonical values of 'order' field: 0..n-1
# Used after deleting a WfModule
def renumber_wf_modules(workflow):
    pos = 0
    for wfm in WfModule.objects.filter(workflow=workflow):
        if wfm.order != pos:
            wfm.order = pos
            wfm.save()
        pos += 1


# --- Commands ----

# The only tricky part AddModule is what we do with the module in backward()
# We detach the WfModule from the workflow, but keep it around for possible later forward()
class AddModuleCommand(Delta):
    # must not have cascade on WfModule because we may delete it first when we are deleted
    wf_module = models.ForeignKey(WfModule, null=True, default=None, blank=True, on_delete=models.SET_DEFAULT)
    order = models.IntegerField()
    applied = models.BooleanField(default=True, null=False)             # is this command currently applied?
    selected_wf_module = models.IntegerField(null=True, blank=True)     # what was selected before we were added?

    def forward_impl(self):
        self.selected_wf_module = self.workflow.selected_wf_module
        insert_wf_module(self.wf_module, self.workflow, self.order)     # may alter wf_module.order without saving
        self.wf_module.workflow = self.workflow                         # attach to workflow
        self.wf_module.save()
        self.workflow.selected_wf_module = self.wf_module.order
        self.workflow.save()
        self.applied = True
        self.save()

    def backward_impl(self):
        self.wf_module.workflow = None                                  # detach from workflow
        self.wf_module.save()
        # [adamhooper, 2018-06-19] I don't think there's any hope we can
        # actually restore selected_wf_module correctly, because sometimes we
        # update it without a command. But we still need to set
        # workflow.selected_wf_module to a _valid_ integer if the
        # currently-selected module is the one we're deleting now and is also
        # the final wf_module in the list.
        self.workflow.selected_wf_module = self.selected_wf_module      # go back to old selection when deleted
        self.workflow.save()
        renumber_wf_modules(self.workflow)                              # fix up ordering on the rest
        self.applied = False
        self.save()

    @staticmethod
    def create(workflow, module_version, insert_before):
        with workflow.cooperative_lock():
            newwfm = WfModule.objects.create(workflow=None, module_version=module_version,
                                             order=insert_before, is_collapsed=False)
            newwfm.create_default_parameters()

            # start EditCells collapsed, just this one module for now
            if (module_version.module.id_name == 'editcells'):
                newwfm.is_collapsed = True

            description = 'Added \'' + module_version.module.name + '\' module'
            delta = Delta.create_impl(AddModuleCommand,
                workflow=workflow,
                wf_module=newwfm,
                order=insert_before,
                command_description=description)

        return delta


# When we are deleted, delete the module if it's not in use by the Workflow (if we are *not* currently applied)
@receiver(pre_delete, sender=AddModuleCommand, dispatch_uid='addmodulecommand')
def addmodulecommand_delete_callback(sender, instance, **kwargs):
    if instance.applied == False:
        instance.wf_module.delete()


delete_lock = threading.Lock()

# Deletion works by simply "orphaning" the wf_module, setting its workflow reference to null
class DeleteModuleCommand(Delta):
    # must not have cascade on WfModule because we may delete it first when we are deleted
    wf_module = models.ForeignKey(WfModule, null=True, default=None, blank=True, on_delete=models.SET_DEFAULT)
    selected_wf_module = models.IntegerField(null=True, blank=True)
    applied = models.BooleanField(default=True, null=False)             # is this command currently applied?

    def forward_impl(self):
        # If we are deleting the selected module, then set the previous module
        # in stack as selected (behavior same as in workflow-reducer.js)
        selected = self.workflow.selected_wf_module
        if selected is not None and selected >= self.wf_module.order:
            selected -= 1
            if selected >= 0:
                self.workflow.selected_wf_module = selected
            else:
                self.workflow.selected_wf_module = None
            self.workflow.save()

        self.wf_module.workflow = None                                  # detach from workflow
        self.wf_module.save()
        renumber_wf_modules(self.workflow)                              # fix up ordering on the rest
        self.applied = True
        self.save()

    def backward_impl(self):
        insert_wf_module(self.wf_module, self.workflow, self.wf_module.order)
        self.wf_module.workflow = self.workflow                         # attach to workflow
        self.wf_module.save()
        # [adamhooper, 2018-06-19] I don't think there's any hope we can
        # actually restore selected_wf_module correctly, because sometimes we
        # update it without a command. But I think focusing the restored module
        # is something a user could expect.
        self.workflow.selected_wf_module = self.selected_wf_module
        self.workflow.save()
        self.applied = False
        self.save()

    @staticmethod
    def create(wf_module):

        # critical section to make double delete check work correctly
        with delete_lock:
            workflow = wf_module.workflow
            if workflow is None:
                return None     # this wfm was already deleted, do nothing

            description = 'Deleted \'' + wf_module.get_module_name() + '\' module'
            delta = Delta.create_impl(
                DeleteModuleCommand,
                workflow=workflow,
                wf_module=wf_module,
                selected_wf_module=workflow.selected_wf_module,
                command_description=description
            )

            return delta

# When we are deleted, delete the module if it's not in use by the Workflow (i.e. if we are currently applied)
@receiver(pre_delete, sender=DeleteModuleCommand, dispatch_uid='deletemodulecommand')
def deletemodulecommand_delete_callback(sender, instance, **kwargs):
    if instance.applied == True:
        try:
            # We've had cases where two DeleteModuleCommands pointed to the same wf, due to race conditions
            # (now fixed via delete_lock). To prevent future similar fails, wrap the delete in a try
            instance.wf_module.delete()
        except Exception as e:
            logger.exception("Error deleting wf_module for DeleteModuleCommand " + str(instance))


class ReorderModulesCommand(Delta):
    # For simplicity and compactness, we store the order of modules as json strings
    # in the same format as the patch request: [ { id: x, order: y}, ... ]
    old_order = models.TextField()
    new_order = models.TextField()

    def apply_order(self, order):
        for record in order:
            wfm = self.workflow.wf_modules.get(pk=record['id']) # may raise WfModule.DoesNotExist if bad ID's
            if wfm.order != record['order']:
                wfm.order = record['order']
                wfm.save()

    def forward_impl(self):
        self.apply_order(json.loads(self.new_order))

    def backward_impl(self):
        self.apply_order(json.loads(self.old_order))

    @staticmethod
    def create(workflow, new_order):
        # Validation: all id's and orders exist and orders are in range 0..n-1
        wfms = WfModule.objects.filter(workflow=workflow)

        ids = [ wfm.id for wfm in wfms]
        for record in new_order:
            if not isinstance(record, dict):
                raise ValueError('JSON data must be an array of {id:x, order:y} objects')
            if 'id' not in record:
                raise ValueError('Missing WfModule id')
            if record['id'] not in ids:
                raise ValueError('Bad WfModule id')
            if 'order' not in record:
                raise ValueError('Missing WfModule order')

        orders = [record['order'] for record in new_order]
        orders.sort()
        if orders != list(range(0, len(orders))):
            raise ValueError('WfModule orders must be in range 0..n-1')

        # Looks good, let's reorder
        delta = Delta.create_impl(
            ReorderModulesCommand,
            workflow=workflow,
            old_order=json.dumps([{'id': wfm.id, 'order': wfm.order} for wfm in wfms]),
            new_order=json.dumps(new_order),
            command_description='Reordered modules'
        )

        return delta


class ChangeDataVersionCommand(Delta):
    wf_module = models.ForeignKey(WfModule, null=True, default=None, blank=True, on_delete=models.SET_DEFAULT)
    old_version = models.DateTimeField('old_version', null=True)    # may not have had a previous version
    new_version = models.DateTimeField('new_version')

    def forward_impl(self):
        self.wf_module.set_fetched_data_version(self.new_version)

    def backward_impl(self):
        self.wf_module.set_fetched_data_version(self.old_version)

    @staticmethod
    def create(wf_module, version):
        description = \
            'Changed \'' + wf_module.get_module_name() + '\' module data version to ' + str(version)

        delta = Delta.create_impl(
            ChangeDataVersionCommand,
            wf_module=wf_module,
            new_version=version,
            old_version=wf_module.get_fetched_data_version(),
            workflow=wf_module.workflow,
            command_description=description
        )

        return delta


class ChangeParameterCommand(Delta):
    parameter_val = models.ForeignKey(ParameterVal, null=True, default=None,
                                      blank=True, on_delete=models.SET_DEFAULT)
    new_value = models.TextField('new_value')
    old_value = models.TextField('old_value')

    # Implement wf_module for self.ws_notify()
    @property
    def wf_module(self):
        return self.parameter_val.wf_module

    def forward_impl(self):
        self.parameter_val.set_value(self.new_value)

    def backward_impl(self):
        self.parameter_val.set_value(self.old_value)

    @staticmethod
    def create(parameter_val, value):
        workflow = parameter_val.wf_module.workflow
        pspec = parameter_val.parameter_spec

        description = \
            'Changed parameter \'' + pspec.name + '\' of \'' + parameter_val.wf_module.get_module_name() + '\' module'

        delta = Delta.create_impl(
            ChangeParameterCommand,
            parameter_val=parameter_val,
            new_value=value,
            old_value=parameter_val.get_value(),
            workflow=workflow,
            command_description=description
        )

        return delta


class ChangeWorkflowTitleCommand(Delta):
    new_value = models.TextField('new_value')
    old_value = models.TextField('old_value')

    def forward_impl(self):
        self.workflow.name = self.new_value
        self.workflow.save()

    def backward_impl(self):
        self.workflow.name = self.old_value
        self.workflow.save()

    @staticmethod
    def create(workflow, name):
        old_name = workflow.name
        description = 'Changed workflow name from ' + old_name + ' to ' + name

        delta = Delta.create_impl(
            ChangeWorkflowTitleCommand,
            workflow=workflow,
            new_value=name,
            old_value=old_name,
            command_description=description
        )

        return delta


class ChangeWfModuleNotesCommand(Delta):
    wf_module = models.ForeignKey(WfModule, null=True, default=None,
                                  blank=True, on_delete=models.SET_DEFAULT)
    new_value = models.TextField('new_value')
    old_value = models.TextField('old_value')

    def forward_impl(self):
        self.wf_module.notes = self.new_value
        self.wf_module.save()

    def backward_impl(self):
        self.wf_module.notes = self.old_value
        self.wf_module.save()

    @staticmethod
    def create(wf_module, notes):
        old_value = wf_module.notes if wf_module.notes else ''
        description = 'Changed workflow module note from ' + old_value + ' to ' + notes

        delta = Delta.create_impl(
            ChangeWfModuleNotesCommand,
            workflow=wf_module.workflow,
            wf_module=wf_module,
            new_value=notes,
            old_value=old_value,
            command_description=description
        )

        return delta


class ChangeWfModuleUpdateSettingsCommand(Delta):
    wf_module = models.ForeignKey(WfModule, null=True, default=None,
                                  blank=True, on_delete=models.SET_DEFAULT)
    new_auto = models.BooleanField()
    old_auto = models.BooleanField()
    new_next_update = models.DateField(null=True)
    old_next_update = models.DateField(null=True)
    new_update_interval = models.IntegerField()
    old_update_interval = models.IntegerField()

    def forward_impl(self):
        self.wf_module.auto_update_data = self.new_auto
        self.wf_module.next_update = self.new_next_update
        self.wf_module.update_interval = self.new_update_interval
        self.wf_module.save()

    def backward_impl(self):
        self.wf_module.auto_update_data = self.old_auto
        self.wf_module.next_update = self.old_next_update
        self.wf_module.update_interval = self.old_update_interval
        self.wf_module.save()

    @staticmethod
    def create(wf_module, auto_update_data, next_update, update_interval):
        description = 'Changed workflow update settings'

        delta = Delta.create_impl(
            ChangeWfModuleUpdateSettingsCommand,
            workflow=wf_module.workflow,
            wf_module=wf_module,
            old_auto=wf_module.auto_update_data,
            new_auto=auto_update_data,
            old_next_update=wf_module.next_update,
            new_next_update=next_update,
            old_update_interval=wf_module.update_interval,
            new_update_interval=update_interval,
            command_description=description
        )

        return delta
