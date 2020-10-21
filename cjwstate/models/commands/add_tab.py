from django.db.models import F

from .base import BaseCommand


class AddTab(BaseCommand):
    """Create a `Tab` and insert it into the Workflow.

    Our "backwards()" logic is to "soft-delete": set `tab.is_deleted=True`.
    Most facets of Workbench's API should pretend a soft-deleted Tab does not
    exist.
    """

    # override
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
        delta.workflow.live_tabs.filter(position__gte=delta.tab.position).update(
            position=F("position") + 1
        )

        delta.tab.is_deleted = False
        delta.tab.save(update_fields=["is_deleted"])

        delta.workflow.selected_tab_position = delta.tab.position
        delta.workflow.save(update_fields=["selected_tab_position"])

    def backward(self, delta):
        delta.tab.is_deleted = True
        delta.tab.save(update_fields=["is_deleted"])

        delta.workflow.live_tabs.filter(position__gt=delta.tab.position).update(
            position=F("position") - 1
        )

        # We know old_selected_tab_position is valid, always
        delta.workflow.selected_tab_position = delta.values_for_backward[
            "old_selected_tab_position"
        ]
        delta.workflow.save(update_fields=["selected_tab_position"])

    def amend_create_kwargs(self, *, workflow: "Workflow", slug: str, name: str):
        # tab starts off "deleted" and appears at end of tabs list; we
        # un-delete in forward().
        tab = workflow.tabs.create(
            position=workflow.live_tabs.count(), is_deleted=True, slug=slug, name=name
        )

        return {
            "workflow": workflow,
            "tab": tab,
            "values_for_backward": {
                "old_selected_tab_position": workflow.selected_tab_position,
            },
        }
