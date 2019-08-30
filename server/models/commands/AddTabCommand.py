from django.db import models
from django.db.models import F
from server.models import Delta, Tab, Workflow
from server.serializers import TabSerializer


class AddTabCommand(Delta):
    """
    Create a `Tab` and insert it into the Workflow.

    Our "backwards()" logic is to "soft-delete": set `tab.is_deleted=True`.
    Most facets of Workbench's API should pretend a soft-deleted Tab does not
    exist.
    """

    # Foreign keys can get a bit confusing. Here we go:
    #
    # * AddTabCommand can only exist if its Tab exists.
    # * Tab depends on Workflow.
    # * AddTabCommand depends on Workflow.
    #
    # So it's safe to delete Commands from a Workflow (as long as the workflow
    # has at least one delta). But it's not safe to delete Tabs -- unless one
    # clears the Deltas first.
    #
    # We set on_delete=PROTECT because if we set on_delete=CASCADE we'd be
    # ambiguous: should one delete the Tab first, or the Delta? The answer is:
    # you _must_ delete the Delta first; after deleting the Delta, you _may_
    # delete the Tab.
    #
    # TODO nix soft-deleting Tabs and WfModules; instead, give DeleteTabCommand
    # all the info it needs to undo itself. Change this field to `tab_slug`.

    class Meta:
        db_table = "server_addtabcommand"

    tab = models.ForeignKey(Tab, on_delete=models.PROTECT)
    old_selected_tab_position = models.IntegerField()

    def load_ws_data(self):
        data = super().load_ws_data()
        if self.tab.is_deleted:
            data["clearTabSlugs"] = [self.tab.slug]
        else:
            data["updateTabs"] = {self.tab.slug: TabSerializer(self.tab).data}
        data["updateWorkflow"]["tab_slugs"] = list(
            self.workflow.live_tabs.values_list("slug", flat=True)
        )
        return data

    def forward_impl(self):
        self.workflow.live_tabs.filter(position__gte=self.tab.position).update(
            position=F("position") + 1
        )

        self.tab.is_deleted = False
        self.tab.save(update_fields=["is_deleted"])

        self.workflow.selected_tab_position = self.tab.position
        self.workflow.save(update_fields=["selected_tab_position"])

    def backward_impl(self):
        self.tab.is_deleted = True
        self.tab.save(update_fields=["is_deleted"])

        self.workflow.live_tabs.filter(position__gt=self.tab.position).update(
            position=F("position") - 1
        )

        # We know old_selected_tab_position is valid, always
        self.workflow.selected_tab_position = self.old_selected_tab_position
        self.workflow.save(update_fields=["selected_tab_position"])

    @classmethod
    def amend_create_kwargs(cls, *, workflow: Workflow, slug: str, name: str):
        # tab starts off "deleted" and appears at end of tabs list; we
        # un-delete in forward().
        tab = workflow.tabs.create(
            position=workflow.live_tabs.count(), is_deleted=True, slug=slug, name=name
        )

        return {
            "workflow": workflow,
            "tab": tab,
            "old_selected_tab_position": workflow.selected_tab_position,
        }
