from django.db import models
from django.db.models import F
from cjwstate.models import Delta, Tab, Workflow


class DeleteTabCommand(Delta):
    """
    Remove `tab` from its Workflow.

    Our logic is to "soft-delete": set `tab.is_deleted=True`. Most facets of
    Workbench's API should pretend a soft-deleted Tab does not exist.
    """

    class Meta:
        app_label = "server"
        db_table = "server_deletetabcommand"

    tab = models.ForeignKey(Tab, on_delete=models.PROTECT)

    # override
    def load_clientside_update(self):
        data = (
            super()
            .load_clientside_update()
            .update_workflow(
                tab_slugs=list(self.workflow.live_tabs.values_list("slug", flat=True))
            )
        )
        if self.tab.is_deleted:
            data = data.clear_tab(self.tab.slug)
        else:
            data = data.replace_tab(self.tab.slug, self.tab.to_clientside())
        return data

    def forward(self):
        self.tab.is_deleted = True
        self.tab.save(update_fields=["is_deleted"])

        self.workflow.live_tabs.filter(position__gt=self.tab.position).update(
            position=F("position") - 1
        )

        if self.workflow.selected_tab_position >= self.tab.position:
            self.workflow.selected_tab_position = max(
                self.workflow.selected_tab_position - 1, 0
            )
            self.workflow.save(update_fields=["selected_tab_position"])

    def backward(self):
        self.workflow.live_tabs.filter(position__gte=self.tab.position).update(
            position=F("position") + 1
        )

        self.tab.is_deleted = False
        self.tab.save(update_fields=["is_deleted"])

        # Focus the un-deleted tab -- because why not
        self.workflow.selected_tab_position = self.tab.position
        self.workflow.save(update_fields=["selected_tab_position"])

    @classmethod
    def amend_create_kwargs(cls, *, workflow: Workflow, tab: Tab):
        if tab.is_deleted:
            return None  # no-op: something raced

        if workflow.live_tabs.count() == 1:
            return None  # no-op: we cannot delete the last tab

        return {"workflow": workflow, "tab": tab}
