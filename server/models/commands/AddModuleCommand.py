from django.db import models
from django.db.models import F
from server.models import Delta, WfModule
from .util import ChangesWfModuleOutputs


# The only tricky part AddModule is what we do with the module in backward()
# We detach the WfModule from the workflow, but keep it around for possible later forward()
class AddModuleCommand(Delta, ChangesWfModuleOutputs):
    # Foreign keys can get a bit confusing. Here we go:
    #
    # * AddModuleCommand can only exist if its WfModule exists.
    # * WfModule depends on Workflow.
    # * AddModuleCommand depends on Workflow.
    #
    # So it's safe to delete Commands from a Workflow (as long as the workflow
    # has at least one delta). But it's not safe to delete WfModules from a
    # workflow -- unless one clears the Deltas first.
    #
    # We set on_delete=PROTECT because if we set on_delete=CASCADE we'd be
    # ambiguous: should one delete the WfModule first, or the Delta? The answer
    # is: you _must_ delete the Delta first; after deleting the Delta, you
    # _may_ delete the WfModule.
    wf_module = models.ForeignKey(WfModule, on_delete=models.PROTECT)

    order = models.IntegerField()
    # what was selected before we were added?
    selected_wf_module = models.IntegerField(null=True, blank=True)
    wf_module_delta_ids = ChangesWfModuleOutputs.wf_module_delta_ids

    @classmethod
    def affected_wf_modules(cls, wf_module) -> models.QuerySet:
        # We don't need to change self.wf_module's delta_id: just the others.
        #
        # At the time this method is called, `wf_module` is "deleted" (well,
        # not yet created).
        return WfModule.objects.filter(workflow_id=wf_module.workflow_id,
                                       order__gte=wf_module.order,
                                       is_deleted=False)

    def forward_impl(self):
        if not self.wf_module.last_relevant_delta_id:
            # We couldn't set self.wf_module.last_relevant_delta_id during
            # creation because `self` (the delta in question) wasn't created.
            # Set it now, before .forward_affected_delta_ids(). After this
            # first write, this Delta should never modify it.
            self.wf_module.last_relevant_delta_id = self.id
            self.wf_module.save(update_fields=['last_relevant_delta_id'])

        self.workflow.live_wf_modules.filter(order__gte=self.wf_module.order) \
            .update(order=F('order') + 1)

        self.wf_module.is_deleted = False
        self.wf_module.save(update_fields=['is_deleted'])

        self.workflow.selected_wf_module = self.wf_module.order
        self.workflow.save(update_fields=['selected_wf_module'])

        self.forward_affected_delta_ids()

    def backward_impl(self):
        self.wf_module.is_deleted = True
        self.wf_module.save(update_fields=['is_deleted'])

        self.workflow.live_wf_modules.filter(order__gt=self.wf_module.order) \
            .update(order=F('order') - 1)

        # [adamhooper, 2018-06-19] I don't think there's any hope we can
        # actually restore selected_wf_module correctly, because sometimes we
        # update it without a command. But we still need to set
        # workflow.selected_wf_module to a _valid_ integer if the
        # currently-selected module is the one we're deleting now and is also
        # the final wf_module in the list.
        self.workflow.selected_wf_module = self.selected_wf_module
        self.workflow.save(update_fields=['selected_wf_module'])

        self.backward_affected_delta_ids()

    def delete(self):
        # Don't let Django batch deletes. We really need to delete in order,
        # because we need to delete AddModuleCommand last so we can
        # garbage-collect its WfModule.
        #
        # TODO let's avoid putting database IDs in deltas! Then we could
        # hard-delete WfModules instead of soft-deleting them.
        try:
            self.next_delta.delete()
        except Delta.DoesNotExist:
            pass

        super().delete()

        if self.wf_module.is_deleted:
            # The WfModule was soft-deleted, and this is the last Delta that
            # references it. After deleting this Delta there are no more pointers
            # to this WfModule. Delete it.
            self.wf_module.delete()

    @classmethod
    def amend_create_kwargs(cls, *, workflow, module_version, insert_before,
                            param_values, **kwargs):
        # wf_module starts off "deleted" and gets un-deleted in forward().
        wf_module = workflow.wf_modules.create(module_version=module_version,
                                               order=insert_before,
                                               is_deleted=True)
        wf_module.create_parametervals(param_values or {})

        wf_module_delta_ids = list(
            workflow.live_wf_modules
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
