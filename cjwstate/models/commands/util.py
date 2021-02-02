from typing import List, Tuple
from django.db.models import Q
from cjwstate.models.workflow import DependencyGraph


class ChangesStepOutputs:
    """Mixin that tracks step.last_relevant_delta_id on affected Steps.

    Usage:

        class MyCommand(ChangesStepOutputs, BaseCommand):  # order matters!
            def amend_create_kwargs(self, *, step, **kwargs):
                # You must store affected_step_delta_ids.
                return {
                    **kwargs,
                    'step': step,
                    'step_delta_ids': self.affected_step_delta_ids(step),
                }

            def forward(self, delta):
                ...
                # update steps in database and store
                # delta._changed_step_delta_ids, for websockets message.
                self.forward_affected_delta_ids(delta)

            def backward(self, delta):
                ...
                # update steps in database and store
                # delta._changed_step_delta_ids, for websockets message.
                self.backward_affected_delta_ids(delta)
    """

    def affected_steps_in_tab(self, step: "Step") -> Q:
        """Filter for Steps _in this Tab_ that this Delta may change.

        The default implementation _includes_ the passed `step`.
        """
        return Q(tab_id=step.tab_id, order__gte=step.order, is_deleted=False)

    def affected_steps_from_tab(self, tab: "Tab") -> Q:
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

    def q_to_step_delta_ids(self, q: Q) -> List[Tuple[int, int]]:
        from ..step import Step

        return list(Step.objects.filter(q).values_list("id", "last_relevant_delta_id"))

    def affected_step_delta_ids(self, step: "Step") -> List[Tuple[int, int]]:
        """List [(step_id, previous_delta_id)] for `step` and deps.

        This is calculated during Delta creation, before it's applied. Be
        careful in AddStep command -- there is no `Delta` in the database, so
        `step.last_relevant_delta_id` is 0 before creation.

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
        this_tab_filter = self.affected_steps_in_tab(step)
        all_tabs_filter = self.affected_steps_from_tab(step.tab)

        q = this_tab_filter | all_tabs_filter
        return self.q_to_step_delta_ids(q)

    def forward_affected_delta_ids(self, delta):
        """Write new last_relevant_delta_id to affected Steps.

        (This usually includes self.step.)
        """
        prev_ids = delta.step_delta_ids

        affected_ids = [pi[0] for pi in prev_ids]

        from ..step import Step

        Step.objects.filter(pk__in=affected_ids).update(last_relevant_delta_id=delta.id)

        # If we have a step in memory, update it.
        if delta.step_id in affected_ids:  # delta.step_id may be None
            delta.step.last_relevant_delta_id = delta.id

        # for websockets notify
        delta._changed_step_versions = [(pi[0], delta.id) for pi in prev_ids]

    def backward_affected_delta_ids(self, delta):
        """Write new last_relevant_delta_id to `step` and its dependents."""
        prev_ids = delta.step_delta_ids

        from ..step import Step

        for step_id, delta_id in prev_ids:
            Step.objects.filter(id=step_id).update(last_relevant_delta_id=delta_id)

            # If we have a step in memory, update it to stay synced with db
            if delta.step_id == step_id:  # delta.step_id may be None
                delta.step.last_relevant_delta_id = delta_id

        # for websockets notify
        delta._changed_step_versions = prev_ids

    def load_clientside_update(self, delta):
        data = super().load_clientside_update(delta)
        for step_id, delta_id in delta._changed_step_versions:
            data = data.update_step(step_id, last_relevant_delta_id=delta_id)

        if delta.step is not None:  # some Commands use it, some don't
            if delta.step.is_deleted or delta.step.tab.is_deleted:
                # When we did or undid this command, we removed the
                # Step from the Workflow.
                data = data.clear_step(delta.step.id)
            else:
                # Serialize _everything_, including params
                #
                # TODO consider serializing only what's changed, so when Alice
                # changes 'has_header' it doesn't overwrite Bob's 'url' while
                # he's editing it.
                data = data.replace_step(delta.step.id, delta.step.to_clientside())

        return data

    def get_modifies_render_output(self, delta) -> None:
        """If any Step output may change, schedule a render over RabbitMQ."""
        return len(delta._changed_step_versions) > 0
