from django.db.models import F, Q

from cjwstate.models.module_registry import MODULE_REGISTRY
from .base import BaseCommand
from .util import ChangesStepOutputs


class AddStep(ChangesStepOutputs, BaseCommand):
    """Create a `Step` and insert it into the Workflow.

    Our "backwards()" logic is to "soft-delete": set
    `step.is_deleted=True`. Most facets of Workbench's API should pretend a
    soft-deleted Steps does not exist.
    """

    # override
    def load_clientside_update(self, delta):
        data = (
            super()
            .load_clientside_update(delta)
            .update_tab(
                delta.step.tab_slug,
                step_ids=list(delta.step.tab.live_steps.values_list("id", flat=True)),
            )
        )
        if delta.step.is_deleted:
            data = data.clear_step(delta.step.id)
        else:
            data = data.replace_step(delta.step.id, delta.step.to_clientside())
        return data

    # override
    def affected_steps_in_tab(self, step) -> Q:
        # We don't need to change self.step's delta_id: just the others.
        #
        # At the time this method is called, `step` is "deleted" (well,
        # not yet created).
        return Q(tab_id=step.tab_id, order__gte=step.order, is_deleted=False)

    def forward(self, delta):
        if not delta.step.last_relevant_delta_id:
            # We couldn't set step.last_relevant_delta_id during Delta creation
            # because `delta` didn't exist at that point.
            # Set it now, before .forward_affected_delta_ids(). After this
            # first write, this Delta should never modify it.
            delta.step.last_relevant_delta_id = delta.id
            delta.step.save(update_fields=["last_relevant_delta_id"])

        # Move subsequent modules over to make way for this one.
        tab = delta.step.tab
        tab.live_steps.filter(order__gte=delta.step.order).update(order=F("order") + 1)

        delta.step.is_deleted = False
        delta.step.save(update_fields=["is_deleted"])

        tab.selected_step_position = delta.step.order
        tab.save(update_fields=["selected_step_position"])

        self.forward_affected_delta_ids(delta)

    def backward(self, delta):
        delta.step.is_deleted = True
        delta.step.save(update_fields=["is_deleted"])

        # Move subsequent modules back to fill the gap created by deleting
        tab = delta.step.tab
        tab.live_steps.filter(order__gt=delta.step.order).update(order=F("order") - 1)

        # Prevent tab.selected_step_position from becoming invalid
        #
        # We can't make this exactly what the user has selected -- that's hard,
        # and it isn't worth the effort. But we _can_ make sure it's valid.
        n_modules = tab.live_steps.count()
        if (
            tab.selected_step_position is None
            or tab.selected_step_position >= n_modules
        ):
            if n_modules == 0:
                tab.selected_step_position = None
            else:
                tab.selected_step_position = n_modules - 1
            tab.save(update_fields=["selected_step_position"])

        self.backward_affected_delta_ids(delta)

    # override
    def get_modifies_render_output(self, delta) -> bool:
        """Force a render.

        Adding a module to an empty workflow, delta._changed_step_versions
        will be None -- and yet we need a render!

        TODO brainstorm other solutions to the original race -- that we can't
        know this delta's ID until after we save it to the database, yet we
        need to save its own ID in delta._changed_step_versions.
        """
        return True

    def amend_create_kwargs(
        self, *, workflow, tab, slug, module_id_name, position, param_values, **kwargs
    ):
        """Add a step to the tab.

        Raise KeyError if `module_id_name` is invalid.

        Raise RuntimeError (unrecoverable) if s3 holds invalid module data.

        Raise ValueError if `param_values` do not match the module's spec.
        """
        from ..step import Step

        # ensure slug is unique, or raise ValueError
        if Step.objects.filter(tab__workflow_id=workflow.id, slug=slug).count() > 0:
            raise ValueError("slug is not unique. Please pass a unique slug.")

        # raise KeyError, RuntimeError
        module_zipfile = MODULE_REGISTRY.latest(module_id_name)
        module_spec = module_zipfile.get_spec()

        # Set _all_ params (not just the user-specified ones). Our
        # dropdown-menu actions only specify the relevant params and expect us
        # to set the others to defaults.
        params = {**module_spec.param_schema.default, **param_values}
        module_spec.param_schema.validate(params)  # raises ValueError

        # step starts off "deleted" and gets un-deleted in forward().
        step = tab.steps.create(
            module_id_name=module_id_name,
            order=position,
            slug=slug,
            is_deleted=True,
            params=params,
            cached_migrated_params=params,
            cached_migrated_params_module_version=module_zipfile.version,
            secrets={},
        )

        return {
            **kwargs,
            "workflow": workflow,
            "step": step,
            "step_delta_ids": self.affected_step_delta_ids(step),
        }
