import logging
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from server.models import Delta, WfModule
from .util import ChangesWfModuleOutputs, insert_wf_module, \
        renumber_wf_modules

logger = logging.getLogger(__name__)


# Deletion works by simply "orphaning" the wf_module, setting its workflow reference to null
class DeleteModuleCommand(Delta, ChangesWfModuleOutputs):
    # must not have cascade on WfModule because we may delete it first when we are deleted
    wf_module = models.ForeignKey(WfModule, null=True, default=None, blank=True, on_delete=models.SET_DEFAULT)
    selected_wf_module = models.IntegerField(null=True, blank=True)
    applied = models.BooleanField(default=True, null=False)             # is this command currently applied?
    dependent_wf_module_last_delta_ids = \
        ChangesWfModuleOutputs.dependent_wf_module_last_delta_ids

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

        self.forward_dependent_wf_module_versions(self.wf_module)
        self.wf_module.workflow = None                                  # detach from workflow
        self.wf_module.save()
        renumber_wf_modules(self.workflow)                              # fix up ordering on the rest
        self.applied = True
        self.save()

    def backward_impl(self):
        insert_wf_module(self.wf_module, self.workflow, self.wf_module.order)
        self.wf_module.workflow = self.workflow                         # attach to workflow
        self.backward_dependent_wf_module_versions(self.wf_module)
        self.wf_module.save()
        # [adamhooper, 2018-06-19] I don't think there's any hope we can
        # actually restore selected_wf_module correctly, because sometimes we
        # update it without a command. But I think focusing the restored module
        # is something a user could expect.
        self.workflow.selected_wf_module = self.selected_wf_module
        self.workflow.save()
        self.applied = False
        self.save()

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


