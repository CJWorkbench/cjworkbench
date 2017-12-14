# A Command changes the state of a Workflow, by producing and executing a Delta

from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from server.models import Workflow, WfModule, ParameterVal, Delta, ModuleVersion
from server.triggerrender import notify_client_workflow_version_changed
import json

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

    def forward(self):
        insert_wf_module(self.wf_module, self.workflow, self.order)     # may alter wf_module.order without saving
        self.wf_module.workflow = self.workflow                         # attach to workflow
        self.wf_module.save()
        self.applied = True
        self.save()

    def backward(self):
        self.wf_module.workflow = None                                  # detach from workflow
        self.wf_module.save()
        renumber_wf_modules(self.workflow)                              # fix up ordering on the rest
        self.applied = False
        self.save()

    @staticmethod
    def create(workflow, module_version, insert_before):
        newwfm = WfModule.objects.create(workflow=None, module_version=module_version,
                                         order=insert_before, is_collapsed=False)
        newwfm.create_default_parameters()

        description = 'Added \'' + module_version.module.name + '\' module'
        delta = AddModuleCommand.objects.create(
            workflow=workflow,
            wf_module=newwfm,
            order=insert_before,
            command_description=description)
        delta.forward()

        notify_client_workflow_version_changed(workflow)
        return delta


# When we are deleted, delete the module if it's not in use by the Workflow (if we are *not* currently applied)
@receiver(pre_delete, sender=AddModuleCommand, dispatch_uid='addmodulecommand')
def addmodulecommand_delete_callback(sender, instance, **kwargs):
    if instance.applied == False:
        instance.wf_module.delete()


# Deletion works by simply "orphaning" the wf_module, setting its workflow reference to null
class DeleteModuleCommand(Delta):
    # must not have cascade on WfModule because we may delete it first when we are deleted
    wf_module = models.ForeignKey(WfModule, null=True, default=None, blank=True, on_delete=models.SET_DEFAULT)
    applied = models.BooleanField(default=True, null=False)             # is this command currently applied?

    def forward(self):
        self.wf_module.workflow = None                                  # detach from workflow
        self.wf_module.save()
        renumber_wf_modules(self.workflow)                              # fix up ordering on the rest
        self.applied = True
        self.save()

    def backward(self):
        insert_wf_module(self.wf_module, self.workflow, self.wf_module.order)
        self.wf_module.workflow = self.workflow                         # attach to workflow
        self.wf_module.save()
        self.applied = False
        self.save()

    @staticmethod
    def create(wf_module):
        description = 'Deleted \'' + wf_module.module_version.module.name + '\' module'

        workflow = wf_module.workflow                                   # about to be set to null, so save it
        delta = DeleteModuleCommand.objects.create(
            workflow=workflow,
            wf_module=wf_module,
            command_description=description)
        delta.forward()
        notify_client_workflow_version_changed(workflow)
        return delta

# When we are deleted, delete the module if it's not in use by the Workflow (if we are currently applied)
@receiver(pre_delete, sender=DeleteModuleCommand, dispatch_uid='deletemodulecommand')
def deletemodulecommand_delete_callback(sender, instance, **kwargs):
    if instance.applied == True:
        instance.wf_module.delete()


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

    def forward(self):
        self.apply_order(json.loads(self.new_order))

    def backward(self):
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
        delta = ReorderModulesCommand.objects.create(
            old_order=json.dumps([ {'id': wfm.id, 'order': wfm.order} for wfm in wfms]),
            new_order=json.dumps(new_order),
            workflow=workflow,
            command_description='Reordered modules')
        delta.forward()

        notify_client_workflow_version_changed(workflow)
        return delta


class ChangeDataVersionCommand(Delta):
    wf_module = models.ForeignKey(WfModule, null=True, default=None, blank=True, on_delete=models.SET_DEFAULT)
    old_version = models.DateTimeField('old_version', null=True)    # may not have had a previous version
    new_version = models.DateTimeField('new_version')

    def forward(self):
        self.wf_module.set_fetched_data_version(self.new_version)

    def backward(self):
        self.wf_module.set_fetched_data_version(self.old_version)

    def rerender_from(self):
        return self.wf_module

    @staticmethod
    def create(wf_module, version):
        description = \
            'Changed \'' + wf_module.module_version.module.name + '\' module data version to ' + str(version)

        delta = ChangeDataVersionCommand.objects.create(
            wf_module=wf_module,
            new_version=version,
            old_version=wf_module.get_fetched_data_version(),
            workflow=wf_module.workflow,
            command_description=description)

        delta.forward()
        notify_client_workflow_version_changed(wf_module.workflow)
        return delta


# Rather than saving off the complete ParameterVal object, we just twiddle the value
class ChangeParameterCommand(Delta):
    parameter_val = models.ForeignKey(ParameterVal, null=True, default=None, blank=True, on_delete=models.SET_DEFAULT)
    new_value = models.TextField('new_value')
    old_value = models.TextField('old_value')

    def forward(self):
        self.parameter_val.set_value(self.new_value)

    def backward(self):
        self.parameter_val.set_value(self.old_value)

    def rerender_from(self):
        return self.parameter_val.wf_module

    @staticmethod
    def create(parameter_val, value):
        workflow = parameter_val.wf_module.workflow
        pspec = parameter_val.parameter_spec

        # We don't create a Delta for derived_data parameter. Such parameters are essentially caches,
        # (e.g. chart output image) and are created either during module render() or in the front end
        # Instead, we just set the value -- and trust that undo-ing the other parameters will also set
        # the derived_data parameters.
        if pspec.derived_data:
            parameter_val.set_value(value)
            return None

        # Not derived data, we're doing this.
        description = \
            'Changed parameter \'' + pspec.name + '\' of \'' + parameter_val.wf_module.module_version.module.name + '\' module'

        delta =  ChangeParameterCommand.objects.create(
            parameter_val=parameter_val,
            new_value=value,
            old_value=parameter_val.get_value(),
            workflow=workflow,
            command_description=description)

        delta.forward()

        # Clear wf_module errors, on the theory that user might have fixed them. The next render()
        # or event() will re-create the errors if there is still a problem. The only other place
        # errors are cleared is when an event is dispatched.
        parameter_val.wf_module.set_ready(notify=False)

        # increment workflow version number, triggers global re-render if this parameter can effect output
        notify = not pspec.ui_only
        if notify:
            notify_client_workflow_version_changed(workflow)

        return delta

class ChangeWorkflowTitleCommand(Delta):
    new_value = models.TextField('new_value')
    old_value = models.TextField('old_value')

    def forward(self):
        self.workflow.name = self.new_value
        self.workflow.save()

    def backward(self):
        self.workflow.name = self.old_value
        self.workflow.save()

    def triggers_rerender(self):
        return False

    @staticmethod
    def create(workflow, name):
        old_name = workflow.name
        description = 'Changed workflow name from ' + old_name + ' to ' + name

        delta = ChangeWorkflowTitleCommand.objects.create(
            workflow = workflow,
            new_value = name,
            old_value = old_name,
            command_description = description
        )

        delta.forward()
        # don't notify client b/c client has already updated UI

        return delta

class ChangeWfModuleNotesCommand(Delta):
    wf_module = models.ForeignKey(WfModule, null=True, default=None, blank=True, on_delete=models.SET_DEFAULT)
    new_value = models.TextField('new_value')
    old_value = models.TextField('old_value')

    def forward(self):
        self.wf_module.notes = self.new_value
        self.wf_module.save()

    def backward(self):
        self.wf_module.notes = self.old_value
        self.wf_module.save()

    def triggers_rerender(self):
        return False

    @staticmethod
    def create(wf_module, notes):
        old_value = wf_module.notes if wf_module.notes else ''
        description = 'Changed workflow module note from ' + old_value + ' to ' + notes

        delta = ChangeWfModuleNotesCommand.objects.create(
            workflow = wf_module.workflow,
            wf_module = wf_module,
            new_value = notes,
            old_value = old_value,
            command_description = description
        )

        delta.forward()
        notify_client_workflow_version_changed(wf_module.workflow)

        return delta

class ChangeWfModuleUpdateSettingsCommand(Delta):
    wf_module = models.ForeignKey(WfModule, null=True, default=None, blank=True, on_delete=models.SET_DEFAULT)
    new_auto = models.BooleanField()
    old_auto = models.BooleanField()
    new_next_update = models.DateField(null=True)
    old_next_update = models.DateField(null=True)
    new_update_interval = models.IntegerField()
    old_update_interval = models.IntegerField()

    def forward(self):
        self.wf_module.auto_update_data = self.new_auto
        self.wf_module.next_update = self.new_next_update
        self.wf_module.update_interval = self.new_update_interval
        self.wf_module.save()

    def backward(self):
        self.wf_module.auto_update_data = self.old_auto
        self.wf_module.next_update = self.old_next_update
        self.wf_module.update_interval = self.old_update_interval
        self.wf_module.save()

    def triggers_rerender(self):
        return False

    @staticmethod
    def create(wf_module, auto_update_data, next_update, update_interval):
        description = 'Changed workflow update settings'

        delta = ChangeWfModuleUpdateSettingsCommand.objects.create(
            workflow = wf_module.workflow,
            wf_module = wf_module,
            old_auto = wf_module.auto_update_data,
            new_auto = auto_update_data,
            old_next_update = wf_module.next_update,
            new_next_update = next_update,
            old_update_interval = wf_module.update_interval,
            new_update_interval = update_interval,
            command_description = description
        )

        delta.forward()
        # No notification needed as client will do update
        # notify_client_workflow_version_changed(wf_module.workflow)

        return delta
