# A Command changes the state of a Workflow, by producing and executing a Delta

from django.db import models
from server.models import Workflow, WfModule, ParameterVal, Delta, ModuleVersion
from server.versions import bump_workflow_version

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


class AddModuleCommand(Delta):
    module_version = models.ForeignKey(ModuleVersion)
    wf_module = models.ForeignKey(WfModule)
    order = models.IntegerField('order')

    def forward(self):
        insert_wf_module(self.wf_module, self.workflow, self.order)     # may alter wf_module.order without saving
        self.wf_module.workflow = self.workflow                         # attach to workflow
        self.wf_module.save()

    def backward(self):
        self.wf_module.workflow = None                                  # detach from workflow
        self.wf_module.save()
        renumber_wf_modules(self.workflow)                              # fix up ordering on the rest

    @staticmethod
    def create(workflow, module_version, insert_before):
        newwfm = WfModule.objects.create(workflow=None, module_version=module_version, order=insert_before)
        newwfm.create_default_parameters()

        description = 'Added \'' + module_version.module.name + '\' module'
        delta = AddModuleCommand.objects.create(
            workflow=workflow,
            wf_module=newwfm,
            module_version=module_version,
            order=insert_before,
            command_description=description)
        delta.forward()

        bump_workflow_version(workflow, notify_client=True)
        return delta


# Deletion works by simply "orphaning" the wf_module, setting its workflow reference to null
class DeleteModuleCommand(Delta):
    wf_module = models.ForeignKey(WfModule)

    def forward(self):
        self.wf_module.workflow = None                                  # detach from workflow
        self.wf_module.save()
        renumber_wf_modules(self.workflow)                              # fix up ordering on the rest

    def backward(self):
        insert_wf_module(self.wf_module, self.workflow, self.wf_module.order)
        self.wf_module.workflow = self.workflow                         # attach to workflow
        self.wf_module.save()

    @staticmethod
    def create(wf_module):
        description = 'Deleted \'' + wf_module.module_version.module.name + '\' module'

        workflow = wf_module.workflow                                   # about to be set to null, so save it
        delta = DeleteModuleCommand.objects.create(
            workflow=workflow,
            wf_module=wf_module,
            command_description=description)
        delta.forward()
        bump_workflow_version(workflow, notify_client=True)
        return delta


# Rather than saving off the complete ParameterVal object, we just twiddle the value
class ChangeParameterCommand(Delta):
    parameter_val = models.ForeignKey(ParameterVal)
    new_value = models.TextField('new_value')
    old_value = models.TextField('old_value')

    def forward(self):
        self.parameter_val.set_value(self.new_value)

    def backward(self):
        self.parameter_val.set_value(self.old_value)

    @staticmethod
    def create(parameter_val, value):
        description = \
            'Changed parameter \'' + parameter_val.parameter_spec.name + '\' of \'' + parameter_val.wf_module.module_version.module.name + '\' module'

        delta =  ChangeParameterCommand.objects.create(
            parameter_val=parameter_val,
            new_value=value,
            old_value=parameter_val.get_value(),
            workflow=parameter_val.wf_module.workflow,
            #revision=parameter_val.wf_module.workflow.revision+1) # does bump_workflow_revision guarantee +1 ?
            command_description=description)

        delta.forward()

        # increment workflow version number, triggers global re-render if this parameter can effect output
        notify = not parameter_val.ui_only
        bump_workflow_version(parameter_val.wf_module.workflow, notify_client=notify)

        return delta




