from django.db import models
from django.db.models import F
from cjwstate.models import Delta, WfModule
from .util import ChangesWfModuleOutputs


class DeleteModuleCommand(ChangesWfModuleOutputs, Delta):
    """
    Remove `wf_module` from its Workflow.

    Our logic is to "soft-delete": set `wf_module.is_deleted=True`. Most facets
    of Workbench's API should pretend a soft-deleted WfModule does not exist.
    """

    class Meta:
        app_label = "server"
        db_table = "server_deletemodulecommand"

    wf_module = models.ForeignKey(WfModule, on_delete=models.PROTECT)
    wf_module_delta_ids = ChangesWfModuleOutputs.wf_module_delta_ids

    def load_ws_data(self):
        data = super().load_ws_data()
        data["updateTabs"] = {
            self.wf_module.tab.slug: {
                "wf_module_ids": list(
                    self.wf_module.tab.live_wf_modules.values_list("id", flat=True)
                )
            }
        }
        return data

    @classmethod
    def affected_wf_modules_in_tab(cls, wf_module) -> models.Q:
        # We don't need to change self.wf_module's delta_id: just the others.
        return models.Q(
            tab_id=wf_module.tab_id, order__gt=wf_module.order, is_deleted=False
        )

    def forward_impl(self):
        # If we are deleting the selected module, then set the previous module
        # in stack as selected (behavior same as in workflow-reducer.js)
        tab = self.wf_module.tab
        selected = tab.selected_wf_module_position
        if selected is not None and selected >= self.wf_module.order:
            selected -= 1
            if selected >= 0:
                tab.selected_wf_module_position = selected
            else:
                tab.selected_wf_module_position = None
            tab.save(update_fields=["selected_wf_module_position"])

        self.wf_module.is_deleted = True
        self.wf_module.save(update_fields=["is_deleted"])

        tab.live_wf_modules.filter(order__gt=self.wf_module.order).update(
            order=F("order") - 1
        )

        self.forward_affected_delta_ids()

    def backward_impl(self):
        tab = self.wf_module.tab

        # Move subsequent modules over to make way for this one.
        tab.live_wf_modules.filter(order__gte=self.wf_module.order).update(
            order=F("order") + 1
        )

        self.wf_module.is_deleted = False
        self.wf_module.save(update_fields=["is_deleted"])

        # Don't set tab.selected_wf_module_position. We can't restore it, and
        # this operation can't invalidate any value that was there previously.

        self.backward_affected_delta_ids()

    @classmethod
    def amend_create_kwargs(cls, *, wf_module, **kwargs):
        # If wf_module is already deleted, ignore this Delta.
        #
        # This works around a race: what if two users delete the same WfModule
        # at the same time? We want only one Delta to be created.
        # amend_create_kwargs() is called within workflow.cooperative_lock(),
        # so we can check without racing whether wf_module is already deleted.
        wf_module.refresh_from_db()
        if wf_module.is_deleted or wf_module.tab.is_deleted:
            return None

        return {
            **kwargs,
            "wf_module": wf_module,
            "wf_module_delta_ids": cls.affected_wf_module_delta_ids(wf_module),
        }

    @property
    def command_description(self):
        return f"Delete WfModule {self.wf_module}"


# You may be wondering why there's no @receiver(pre_delete, ...) here. That's
# because if we're deleting a DeleteModuleCommand, then that means _previous_
# Deltas assume the WfModule exists. We must always delete Deltas in reverse
# order, from most-recent to least-recent. Only AddModuleCommand should delete
# a WfModule.
#
# Don't delete the WfModule here. That would break every other Delta.
