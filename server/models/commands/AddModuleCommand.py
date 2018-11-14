from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from server.models import Delta, WfModule
from .util import ChangesWfModuleOutputs, insert_wf_module, \
        renumber_wf_modules

# The only tricky part AddModule is what we do with the module in backward()
# We detach the WfModule from the workflow, but keep it around for possible later forward()
class AddModuleCommand(Delta, ChangesWfModuleOutputs):
    # must not have cascade on WfModule because we may delete it first when we are deleted
    wf_module = models.ForeignKey(WfModule, null=True, default=None,
                                  blank=True, on_delete=models.SET_DEFAULT)
    order = models.IntegerField()
    selected_wf_module = models.IntegerField(null=True, blank=True)     # what was selected before we were added?
    dependent_wf_module_last_delta_ids = \
        ChangesWfModuleOutputs.dependent_wf_module_last_delta_ids

    def forward_impl(self):
        self.selected_wf_module = self.workflow.selected_wf_module
        insert_wf_module(self.wf_module, self.workflow, self.order)     # may alter wf_module.order without saving
        self.wf_module.workflow = self.workflow                         # attach to workflow
        self.forward_dependent_wf_module_versions(self.wf_module)
        self.wf_module.save()
        self.workflow.selected_wf_module = self.wf_module.order
        self.workflow.save()
        self.save()

    def backward_impl(self):
        self.backward_dependent_wf_module_versions(self.wf_module)
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
        self.save()

    @classmethod
    async def create(cls, workflow, module_version, insert_before,
                     param_values):
        newwfm = WfModule.objects.create(workflow=None,
                                         module_version=module_version,
                                         order=insert_before,
                                         is_collapsed=False)
        newwfm.create_parametervals(param_values or {})

        delta = await cls.create_impl(workflow=workflow, wf_module=newwfm,
                                      order=insert_before)

        return delta

    @property
    def command_description(self):
        return f'Add WfModule {self.wf_module}'


# Delete the module when we are deleted. This assumes we're only deleted if we
# haven't been applied.
@receiver(pre_delete, sender=AddModuleCommand, dispatch_uid='addmodulecommand')
def addmodulecommand_delete_callback(sender, instance, **kwargs):
    instance.wf_module.delete()
