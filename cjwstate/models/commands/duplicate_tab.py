from django.db import IntegrityError
from django.db.models import F

from .base import BaseCommand


class DuplicateTab(BaseCommand):
    """Create a `Tab` copying the contents of another Tab.

    Our "backwards()" logic is to "soft-delete": set `tab.is_deleted=True`.
    Most facets of Workbench's API should pretend a sort-deleted Tab does not
    exist.
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
            step_ids = list(
                # tab.live_steps can be nonempty even when tab.is_deleted
                delta.tab.live_steps.values_list("id", flat=True)
            )
            return data.clear_tab(delta.tab.slug).clear_steps(step_ids)
        else:
            return data.replace_tab(
                delta.tab.slug, delta.tab.to_clientside()
            ).replace_steps(
                {step.id: step.to_clientside() for step in delta.tab.live_steps}
            )

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

    def get_modifies_render_output(self, delta) -> bool:
        """Execute if we added a module that isn't rendered.

        The common case -- duplicating an already-rendered tab, or possibly an
        empty tab -- doesn't require an execute because all modules are
        up-to-date.

        We do not need to schedule a render after deleting the tab, because all
        modified modules don't exist -- therefore they're up to date.

        This must be called in a `workflow.cooperative_lock()`.
        """
        return not delta.tab.is_deleted and any(
            step.last_relevant_delta_id != step.cached_render_result_delta_id
            for step in delta.tab.live_steps.all()
        )

    def amend_create_kwargs(
        self, *, workflow: "Workflow", from_tab: "Tab", slug: str, name: str
    ):
        """Create a duplicate of `from_tab`."""
        # tab starts off "deleted" and appears at end of tabs list; we
        # un-delete in forward().
        try:
            tab = workflow.tabs.create(
                slug=slug,
                name=name,
                position=from_tab.position + 1,
                selected_step_position=from_tab.selected_step_position,
                is_deleted=True,
            )
        except IntegrityError:
            raise ValueError('tab slug "%s" is already used' % slug)
        for step in from_tab.live_steps:
            step.duplicate_into_same_workflow(tab)

        # A note on the last_relevant_delta_id of the new Steps:
        #
        # Step.duplicate_into_same_workflow() will set all
        # `last_relevant_delta_id` to `workflow.last_delta_id`, which doesn't
        # consider this DuplicateTabCommand. That's "incorrect", but it doesn't
        # matter: `last_relevant_delta_id` is really a "cache ID", not "Delta
        # ID" (it isn't even a foreign key), and workflow.last_delta_id is fine
        # for that use.
        #
        # After duplicate, we don't need to invalidate any Steps in any other
        # Tabs. (They can't depend on the steps this Command creates, since the
        # steps don't exist yet.) And during undo, likewise, we don't need to
        # re-render because no other Tabs can depend on this one at the time we
        # Undo (since after .forward(), no other Tabs depend on this one).
        #
        # TL;DR do nothing. Undo/redo will sort itself out.

        return {
            "workflow": workflow,
            "tab": tab,
            "values_for_backward": {
                "old_selected_tab_position": workflow.selected_tab_position,
            },
        }
