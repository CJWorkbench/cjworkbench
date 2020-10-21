from django.db.models import F

from .base import BaseCommand


class DeleteTab(BaseCommand):
    """Remove `tab` from its Workflow.

    Our logic is to "soft-delete": set `tab.is_deleted=True`. Most facets of
    Workbench's API should pretend a soft-deleted Tab does not exist.
    """

    def load_clientside_update(self, delta):
        data = (
            super()
            .load_clientside_update(delta)
            .update_workflow(
                tab_slugs=list(delta.workflow.live_tabs.values_list("slug", flat=True))
            )
        )
        if delta.tab.is_deleted:
            data = data.clear_tab(delta.tab.slug)
        else:
            data = data.replace_tab(delta.tab.slug, delta.tab.to_clientside())
        return data

    def forward(self, delta):
        delta.tab.is_deleted = True
        delta.tab.save(update_fields=["is_deleted"])

        delta.workflow.live_tabs.filter(position__gt=delta.tab.position).update(
            position=F("position") - 1
        )

        if delta.workflow.selected_tab_position >= delta.tab.position:
            delta.workflow.selected_tab_position = max(
                delta.workflow.selected_tab_position - 1, 0
            )
            delta.workflow.save(update_fields=["selected_tab_position"])

    def backward(self, delta):
        delta.workflow.live_tabs.filter(position__gte=delta.tab.position).update(
            position=F("position") + 1
        )

        delta.tab.is_deleted = False
        delta.tab.save(update_fields=["is_deleted"])

        # Focus the un-deleted tab -- because why not
        delta.workflow.selected_tab_position = delta.tab.position
        delta.workflow.save(update_fields=["selected_tab_position"])

    def amend_create_kwargs(self, *, workflow: "Workflow", tab: "Tab"):
        if tab.is_deleted:
            return None  # no-op: something raced

        if workflow.live_tabs.count() == 1:
            return None  # no-op: we cannot delete the last tab

        return {"workflow": workflow, "tab": tab}
