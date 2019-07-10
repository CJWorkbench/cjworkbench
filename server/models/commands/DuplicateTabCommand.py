from django.db import models, IntegrityError
from django.db.models import F
from server.models import Delta, Tab, Workflow
from server.serializers import TabSerializer, WfModuleSerializer


class DuplicateTabCommand(Delta):
    """
    Create a `Tab` copying the contents of another Tab.

    Our "backwards()" logic is to "soft-delete": set `tab.is_deleted=True`.
    Most facets of Workbench's API should pretend a sort-deleted Tab does not
    exist.
    """

    # Foreign keys can get a bit confusing. Here we go:
    #
    # * DuplicateTabCommand can only exist if its Tab exists.
    # * Tab depends on Workflow.
    # * DuplicateTabCommand depends on Workflow.
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
    tab = models.ForeignKey(Tab, on_delete=models.PROTECT)
    old_selected_tab_position = models.IntegerField()

    def load_ws_data(self):
        workflow_data = {
            **self._load_workflow_ws_data(),
            "tab_slugs": list(self.workflow.live_tabs.values_list("slug", flat=True)),
        }
        if self.tab.is_deleted:
            wfm_ids = list(
                # tab.live_wf_modules can be nonempty even when tab.is_deleted
                self.tab.live_wf_modules.values_list("id", flat=True)
            )
            return {
                "updateWorkflow": workflow_data,
                "clearTabSlugs": [self.tab.slug],
                "clearWfModuleIds": [str(wfm_id) for wfm_id in wfm_ids],
            }
        else:
            return {
                "updateWorkflow": workflow_data,
                "updateTabs": {self.tab.slug: TabSerializer(self.tab).data},
                "updateWfModules": {
                    str(wfm.id): WfModuleSerializer(wfm).data
                    for wfm in self.tab.live_wf_modules
                },
            }

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

    # override
    async def schedule_execute_if_needed(self) -> None:
        """
        Execute if we added a module that isn't rendered.
        
        The common case -- duplicating an already-rendered tab, or possibly an
        empty tab -- doesn't require an execute because all modules are
        up-to-date.

        We do not need to schedule a render after deleting the tab, because all
        modified modules don't exist -- therefore they're up to date.
        """
        if not self.tab.is_deleted and any(
            wfm.last_relevant_delta_id != wfm.cached_render_result_delta_id
            for wfm in self.tab.live_wf_modules.all()
        ):
            await self._schedule_execute()

    @classmethod
    def amend_create_kwargs(
        cls, *, workflow: Workflow, from_tab: Tab, slug: str, name: str
    ):
        """
        Create a duplicate of `from_tab`.
        """
        # tab starts off "deleted" and appears at end of tabs list; we
        # un-delete in forward().
        try:
            tab = workflow.tabs.create(
                slug=slug,
                name=name,
                position=from_tab.position + 1,
                selected_wf_module_position=from_tab.selected_wf_module_position,
                is_deleted=True,
            )
        except IntegrityError:
            raise ValueError('tab slug "%s" is already used' % slug)
        for wf_module in from_tab.live_wf_modules:
            wf_module.duplicate(tab)

        # A note on the last_relevant_delta_id of the new WfModules:
        #
        # WfModule.duplicate() will set all the `last_relevant_delta_id` to
        # `self.workflow.last_delta_id`, which is the delta _before_ this
        # DuplicateTabCommand. That's "incorrect", but it doesn't really
        # matter: `last_relevant_delta_id` is really a "cache ID", not "Delta
        # ID" (it isn't even a foreign key), and workflow.last_delta_id is fine
        # for that use.
        #
        # After duplicate, we don't need to invalidate any WfModules in any
        # other Tabs. (They can't depend on the steps this Command creates,
        # since te steps don't exist yet.) And during undo, likewise, we don't
        # need to re-render because no other Tabs can depend on this one at the
        # time we Undo (since after .forward(), no other Tabs depend on this
        # one).
        #
        # TL;DR do nothing. Undo/redo will sort itself out.

        return {
            "workflow": workflow,
            "tab": tab,
            "old_selected_tab_position": workflow.selected_tab_position,
        }
