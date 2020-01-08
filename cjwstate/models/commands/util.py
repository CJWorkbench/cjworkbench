from typing import List, Tuple
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Q
from cjwstate.models import Tab, WfModule
from cjwstate.models.workflow import DependencyGraph
from server.serializers import WfModuleSerializer


class ChangesWfModuleOutputs:
    """
    Mixin that tracks wf_module.last_relevant_delta_id on affected WfModules.

    Usage:

        class MyCommand(ChangesWfModuleOutputs, Delta):  # order matters!
            wf_module_delta_ids = ChangesWfModuleOutputs.wf_module_delta_ids

            # override
            @classmethod
            def amend_create_kwargs(cls, *, wf_module, **kwargs):
                # You must store affected_wf_module_delta_ids.
                return {
                    **kwargs,
                    'wf_module': wf_module,
                    'wf_module_delta_ids':
                        cls.affected_wf_module_delta_ids(wf_module),
                }

            def forward(self):
                ...
                # update wf_modules in database and store
                # self._changed_wf_module_delta_ids, for websockets message.
                self.forward_affected_delta_ids()

            def backward(self):
                ...
                # update wf_modules in database and store
                # self._changed_wf_module_delta_ids, for websockets message.
                self.backward_affected_delta_ids()
    """

    # List of (id, last_relevant_delta_id) for WfModules, pre-`forward()`.
    wf_module_delta_ids = ArrayField(ArrayField(models.IntegerField(), size=2))

    @classmethod
    def affected_wf_modules_in_tab(cls, wf_module) -> Q:
        """
        Filter for WfModules _in this Tab_ that this Delta may change.

        The default implementation _includes_ the passed `wf_module`.
        """
        return Q(tab_id=wf_module.tab_id, order__gte=wf_module.order, is_deleted=False)

    @classmethod
    def affected_wf_modules_from_tab(cls, tab: Tab) -> Q:
        """
        Filter for WfModules depending on `tab`.

        In other words: all WfModules that use `tab` in a 'tab' parameter, plus
        all WfModules that depend on them.

        This uses the tab's workflow's `DependencyGraph`.
        """
        graph = DependencyGraph.load_from_workflow(tab.workflow)
        tab_slug = tab.slug
        wf_module_ids = graph.get_step_ids_depending_on_tab_slug(tab_slug)

        # You'd _think_ a Delta could change the dependency graph in a way we
        # can't detect. But [adamhooper, 2019-02-07] I don't think it can. In
        # particular, if this Delta is about to create or fix a cycle, then all
        # the nodes in the cycle are there both before _and_ after the change.
        #
        # So assume `wf_module_ids` is complete here. If we notice some modules
        # not updating correctly, we'll have to revisit this. I haven't proved
        # anything, and I don't know whether future Deltas might break this
        # assumption.

        return Q(id__in=wf_module_ids)

    @classmethod
    def q_to_wf_module_delta_ids(cls, q: Q) -> List[Tuple[int, int]]:
        return list(
            WfModule.objects.filter(q).values_list("id", "last_relevant_delta_id")
        )

    @classmethod
    def affected_wf_module_delta_ids(cls, wf_module: WfModule) -> List[Tuple[int, int]]:
        """
        List [(wf_module_id, previous_delta_id)] for `wf_module` and deps.

        This is calculated during Delta creation, before it's applied. Be
        careful in AddModuleCommand -- there is no `Delta` in the database, so
        `wf_module.last_relevant_delta_id` is NULL before creation.

        To list WfModules that depend on `wf_module`, we go through two phases:

            1. Call `affected_wf_modules_in_tab()`. This gives the module's
               successors within the tab.
            2. Use the entire Workflow's `DependencyGraph` to find modules that
               rely on `wf_module.tab` (recursively).

        Then we query the `last_relevant_delta_id` from all those affected
        steps and store them with the Delta. When we forward() the Delta, we'll
        set all those steps to the new Delta, so they all get re-rendered. When
        we backward() the Delta, we'll revert to the IDs we save here.
        """
        this_tab_filter = cls.affected_wf_modules_in_tab(wf_module)
        all_tabs_filter = cls.affected_wf_modules_from_tab(wf_module.tab)

        q = this_tab_filter | all_tabs_filter
        return cls.q_to_wf_module_delta_ids(q)

    def forward_affected_delta_ids(self):
        """
        Write new last_relevant_delta_id to affected WfModules.

        (This usually includes self.wf_module.)
        """
        prev_ids = self.wf_module_delta_ids

        affected_ids = [pi[0] for pi in prev_ids]

        WfModule.objects.filter(pk__in=affected_ids).update(
            last_relevant_delta_id=self.id
        )

        # If we have a wf_module in memory, update it.
        if hasattr(self, "wf_module_id") and self.wf_module_id in affected_ids:
            self.wf_module.last_relevant_delta_id = self.id

        # for websockets notify
        self._changed_wf_module_versions = [(pi[0], self.id) for pi in prev_ids]

    def backward_affected_delta_ids(self):
        """
        Write new last_relevant_delta_id to `wf_module` and its dependents.
        """
        prev_ids = self.wf_module_delta_ids

        for wfm_id, delta_id in prev_ids:
            WfModule.objects.filter(id=wfm_id).update(last_relevant_delta_id=delta_id)

            if hasattr(self, "wf_module_id") and wfm_id == self.wf_module_id:
                # If we have a wf_module in memory, update it
                self.wf_module.last_relevant_delta_id = delta_id

        # for websockets notify
        self._changed_wf_module_versions = prev_ids

    # override Delta
    def load_ws_data(self):
        data = {
            "updateWorkflow": self._load_workflow_ws_data(),
            "updateWfModules": {
                str(wfm_id): {
                    "last_relevant_delta_id": delta_id,
                    "output_columns": [],
                    "output_errors": [],
                    "output_status": "busy",
                    "output_n_rows": 0,
                }
                for wfm_id, delta_id in self._changed_wf_module_versions
            },
        }

        if hasattr(self, "wf_module"):
            if self.wf_module.is_deleted or self.wf_module.tab.is_deleted:
                # When we did or undid this command, we removed the
                # WfModule from the Workflow.
                data["clearWfModuleIds"] = [self.wf_module_id]
            else:
                # Serialize _everything_, including params
                #
                # TODO consider serializing only what's changed, so when Alice
                # changes 'has_header' it doesn't overwrite Bob's 'url' while
                # he's editing it.
                step_data = WfModuleSerializer(self.wf_module).data
                data["updateWfModules"][str(self.wf_module_id)] = step_data

        return data

    # override Delta
    def get_modifies_render_output(self) -> None:
        """
        If any WfModule output may change, schedule a render over RabbitMQ.
        """
        return len(self._changed_wf_module_versions) > 0
