from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from server.models import Delta, WfModule
from .util import ChangesWfModuleOutputs, insert_wf_module, renumber_wf_modules


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
    wf_module_delta_ids = ChangesWfModuleOutputs.wf_module_delta_ids

    @classmethod
    def affected_wf_modules(cls, wf_module) -> models.QuerySet:
        # We don't need to change self.wf_module's delta_id: just the others.
        #
        # At the time this method is called, `wf_module` is "deleted" (well,
        # not yet created).
        return wf_module.workflow.wf_modules.filter(order__gte=wf_module.order)

    def forward_impl(self):
        if not self.wf_module.last_relevant_delta_id:
            # We couldn't set self.wf_module.last_relevant_delta_id during
            # creation because `self` (the delta in question) wasn't created.
            # Set it now, before .forward_affected_delta_ids(). After this
            # first write, this Delta should never modify it.
            self.wf_module.last_relevant_delta_id = self.id
            self.wf_module.save(update_fields=['last_relevant_delta_id'])

        insert_wf_module(self.wf_module, self.workflow, self.order)
        self.wf_module.workflow = self.workflow  # attach to workflow
        self.wf_module.save(update_fields=['workflow_id'])

        self.workflow.selected_wf_module = self.wf_module.order
        self.workflow.save(update_fields=['selected_wf_module'])

        # forward after insert -- for dependent_wf_module_last_delta_ids
        self.forward_affected_delta_ids(self.wf_module)

    def backward_impl(self):
        # Backward before removing module from self.workflow
        self.backward_affected_delta_ids(self.wf_module)

        self.wf_module.workflow = None  # detach from workflow
        self.wf_module.save(update_fields=['workflow_id'])

        # [adamhooper, 2018-06-19] I don't think there's any hope we can
        # actually restore selected_wf_module correctly, because sometimes we
        # update it without a command. But we still need to set
        # workflow.selected_wf_module to a _valid_ integer if the
        # currently-selected module is the one we're deleting now and is also
        # the final wf_module in the list.
        self.workflow.selected_wf_module = self.selected_wf_module
        self.workflow.save(update_fields=['selected_wf_module'])

        renumber_wf_modules(self.workflow) # fix up ordering on the rest

    @classmethod
    def amend_create_kwargs(cls, *, workflow, module_version, insert_before,
                            param_values, **kwargs):
        wf_module = WfModule.objects.create(workflow=None,
                                            module_version=module_version,
                                            order=insert_before,
                                            is_collapsed=False)
        wf_module.create_parametervals(param_values or {})

        # wf_module.workflow is None, so gather wf_module_delta_ids manually
        wf_module_delta_ids = list(
            workflow.wf_modules
                .filter(order__gte=insert_before)
                .values_list('id', 'last_relevant_delta_id')
        )

        return {
            **kwargs,
            'workflow': workflow,
            'wf_module': wf_module,
            'order': insert_before,
            'selected_wf_module': workflow.selected_wf_module,
            'wf_module_delta_ids': wf_module_delta_ids,
        }

    @classmethod
    async def create(cls, workflow, module_version, insert_before,
                     param_values):
        return await cls.create_impl(workflow=workflow,
                                     module_version=module_version,
                                     insert_before=insert_before,
                                     param_values=param_values)

    @property
    def command_description(self):
        return f'Add WfModule {self.wf_module}'


# Delete the module when we are deleted. This assumes we're only deleted if we
# haven't been applied.
#
# Use post_delete: if we use pre_delete then we'll clear command.wf_module (the
# foreign key).
@receiver(post_delete, sender=AddModuleCommand, dispatch_uid='addmodulecommand')
def addmodulecommand_delete_callback(sender, instance, **kwargs):
    instance.wf_module.delete()
