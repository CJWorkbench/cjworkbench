from typing import List, Tuple
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Q
from cjwstate.models import Tab, Step
from cjwstate.models.workflow import DependencyGraph


class ChangesStepOutputs:
    """Mixin that tracks step.last_relevant_delta_id on affected Steps.

    Usage:

        class MyCommand(ChangesStepOutputs, Delta):  # order matters!
            step_delta_ids = ChangesStepOutputs.step_delta_ids

            # override
            @classmethod
            def amend_create_kwargs(cls, *, step, **kwargs):
                # You must store affected_step_delta_ids.
                return {
                    **kwargs,
                    'step': step,
                    'step_delta_ids':
                        cls.affected_step_delta_ids(step),
                }

            def forward(self):
                ...
                # update steps in database and store
                # self._changed_step_delta_ids, for websockets message.
                self.forward_affected_delta_ids()

            def backward(self):
                ...
                # update steps in database and store
                # self._changed_step_delta_ids, for websockets message.
                self.backward_affected_delta_ids()
    """

    # List of (id, last_relevant_delta_id) for Steps, pre-`forward()`.
    step_delta_ids = ArrayField(ArrayField(models.IntegerField(), size=2))

    @classmethod
    def affected_steps_in_tab(cls, step) -> Q:
        """Filter for Steps _in this Tab_ that this Delta may change.

        The default implementation _includes_ the passed `step`.
        """
        return Q(tab_id=step.tab_id, order__gte=step.order, is_deleted=False)

    @classmethod
    def affected_steps_from_tab(cls, tab: Tab) -> Q:
        """Filter for Steps depending on `tab`.

        In other words: all Steps that use `tab` in a 'tab' parameter, plus
        all Steps that depend on them.

        This uses the tab's workflow's `DependencyGraph`.
        """
        graph = DependencyGraph.load_from_workflow(tab.workflow)
        tab_slug = tab.slug
        step_ids = graph.get_step_ids_depending_on_tab_slug(tab_slug)

        # You'd _think_ a Delta could change the dependency graph in a way we
        # can't detect. But [adamhooper, 2019-02-07] I don't think it can. In
        # particular, if this Delta is about to create or fix a cycle, then all
        # the nodes in the cycle are there both before _and_ after the change.
        #
        # So assume `step_ids` is complete here. If we notice some modules
        # not updating correctly, we'll have to revisit this. I haven't proved
        # anything, and I don't know whether future Deltas might break this
        # assumption.

        return Q(id__in=step_ids)

    @classmethod
    def q_to_step_delta_ids(cls, q: Q) -> List[Tuple[int, int]]:
        return list(Step.objects.filter(q).values_list("id", "last_relevant_delta_id"))

    @classmethod
    def affected_step_delta_ids(cls, step: Step) -> List[Tuple[int, int]]:
        """List [(step_id, previous_delta_id)] for `step` and deps.

        This is calculated during Delta creation, before it's applied. Be
        careful in AddModuleCommand -- there is no `Delta` in the database, so
        `step.last_relevant_delta_id` is NULL before creation.

        To list Steps that depend on `step`, we go through two phases:

            1. Call `affected_steps_in_tab()`. This gives the module's
               successors within the tab.
            2. Use the entire Workflow's `DependencyGraph` to find modules that
               rely on `step.tab` (recursively).

        Then we query the `last_relevant_delta_id` from all those affected
        steps and store them with the Delta. When we forward() the Delta, we'll
        set all those steps to the new Delta, so they all get re-rendered. When
        we backward() the Delta, we'll revert to the IDs we save here.
        """
        this_tab_filter = cls.affected_steps_in_tab(step)
        all_tabs_filter = cls.affected_steps_from_tab(step.tab)

        q = this_tab_filter | all_tabs_filter
        return cls.q_to_step_delta_ids(q)

    def forward_affected_delta_ids(self):
        """Write new last_relevant_delta_id to affected Steps.

        (This usually includes self.step.)
        """
        prev_ids = self.step_delta_ids

        affected_ids = [pi[0] for pi in prev_ids]

        Step.objects.filter(pk__in=affected_ids).update(last_relevant_delta_id=self.id)

        # If we have a step in memory, update it.
        if hasattr(self, "step_id") and self.step_id in affected_ids:
            self.step.last_relevant_delta_id = self.id

        # for websockets notify
        self._changed_step_versions = [(pi[0], self.id) for pi in prev_ids]

    def backward_affected_delta_ids(self):
        """Write new last_relevant_delta_id to `step` and its dependents."""
        prev_ids = self.step_delta_ids

        for step_id, delta_id in prev_ids:
            Step.objects.filter(id=step_id).update(last_relevant_delta_id=delta_id)

            if hasattr(self, "step_id") and step_id == self.step_id:
                # If we have a step in memory, update it
                self.step.last_relevant_delta_id = delta_id

        # for websockets notify
        self._changed_step_versions = prev_ids

    # override Delta
    def load_clientside_update(self):
        data = super().load_clientside_update()
        for step_id, delta_id in self._changed_step_versions:
            data = data.update_step(step_id, last_relevant_delta_id=delta_id)

        if hasattr(self, "step"):
            if self.step.is_deleted or self.step.tab.is_deleted:
                # When we did or undid this command, we removed the
                # Step from the Workflow.
                data = data.clear_step(self.step.id)
            else:
                # Serialize _everything_, including params
                #
                # TODO consider serializing only what's changed, so when Alice
                # changes 'has_header' it doesn't overwrite Bob's 'url' while
                # he's editing it.
                data = data.replace_step(self.step.id, self.step.to_clientside())

        return data

    # override Delta
    def get_modifies_render_output(self) -> None:
        """If any Step output may change, schedule a render over RabbitMQ."""
        return len(self._changed_step_versions) > 0
