from django.db import models
from server.models import Delta, WfModule
from .util import ChangesWfModuleOutputs, insert_wf_module, renumber_wf_modules


# Deletion works by simply "orphaning" the wf_module, setting its workflow reference to null
class DeleteModuleCommand(Delta, ChangesWfModuleOutputs):
    # TODO set null=False. null=True makes no sense.
    wf_module = models.ForeignKey(WfModule, null=True, default=None,
                                  blank=True, on_delete=models.PROTECT)
    selected_wf_module = models.IntegerField(null=True, blank=True)
    dependent_wf_module_last_delta_ids = \
        ChangesWfModuleOutputs.dependent_wf_module_last_delta_ids
    wf_module_delta_ids = ChangesWfModuleOutputs.wf_module_delta_ids

    @classmethod
    def affected_wf_modules(cls, wf_module) -> models.QuerySet:
        # We don't need to change self.wf_module's delta_id: just the others.
        return wf_module.workflow.wf_modules.filter(order__gt=wf_module.order)

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

        # forward before delete -- for dependent_wf_module_last_delta_ids
        self.forward_affected_delta_ids(self.wf_module)

        self.wf_module.workflow = None  # detach from workflow
        self.wf_module.save(update_fields=['workflow_id'])

        renumber_wf_modules(self.workflow)  # fix up ordering on the rest

    def backward_impl(self):
        insert_wf_module(self.wf_module, self.workflow, self.wf_module.order)

        self.wf_module.workflow = self.workflow  # attach to workflow
        self.wf_module.save(update_fields=['workflow_id'])

        self.backward_affected_delta_ids(self.wf_module)

        # [adamhooper, 2018-06-19] I don't think there's any hope we can
        # actually restore selected_wf_module correctly, because sometimes we
        # update it without a command. But I think focusing the restored module
        # is something a user could expect.
        self.workflow.selected_wf_module = self.selected_wf_module
        self.workflow.save(update_fields=['selected_wf_module'])

    @classmethod
    def amend_create_kwargs(cls, *, workflow, wf_module):
        # If wf_module is already deleted, ignore this Delta.
        #
        # This works around a race: what if two users delete the same WfModule
        # at the same time? We want only one Delta to be created.
        # amend_create_kwargs() is called within workflow.cooperative_lock(),
        # so we can check without racint whether wf_module is already deleted.
        wf_module.refresh_from_db()
        if not wf_module.workflow_id:
            return None

        return {
            'workflow': workflow,
            'wf_module': wf_module,
            'selected_wf_module': workflow.selected_wf_module,
            'wf_module_delta_ids': cls.affected_wf_module_delta_ids(wf_module),
        }

    @classmethod
    async def create(cls, wf_module):
        return await cls.create_impl(
            workflow=wf_module.workflow,
            wf_module=wf_module,
        )

    @property
    def command_description(self):
        return f'Delete WfModule {self.wf_module}'

# You may be wondering why there's no @receiver(pre_delete, ...) here. That's
# because if we're deleting a DeleteModuleCommand, then that means _previous_
# Deltas assume the WfModule exists. We must always delete Deltas in reverse
# order, from most-recent to least-recent. Only AddModuleCommand should delete
# a WfModule.
#
# Don't delete the WfModule here. That would break every other Delta.
