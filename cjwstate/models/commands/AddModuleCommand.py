from django.db import models
from django.db.models import F
from cjwstate.models.module_registry import MODULE_REGISTRY
from ..delta import Delta
from ..step import Step
from .util import ChangesStepOutputs


class AddModuleCommand(ChangesStepOutputs, Delta):
    """Create a `Step` and insert it into the Workflow.

    Our "backwards()" logic is to "soft-delete": set
    `step.is_deleted=True`. Most facets of Workbench's API should pretend a
    soft-deleted Steps does not exist.
    """

    # Foreign keys can get a bit confusing. Here we go:
    #
    # * AddModuleCommand can only exist if its Step exists.
    # * Step depends on Workflow.
    # * AddModuleCommand depends on Workflow.
    #
    # So it's safe to delete Commands from a Workflow (as long as the workflow
    # has at least one delta). But it's not safe to delete Steps from a
    # workflow -- unless one clears the Deltas first.
    #
    # We set on_delete=PROTECT because if we set on_delete=CASCADE we'd be
    # ambiguous: should one delete the Step first, or the Delta? The answer
    # is: you _must_ delete the Delta first; after deleting the Delta, you
    # _may_ delete the Step.

    class Meta:
        app_label = "server"
        db_table = "server_addmodulecommand"

    step = models.ForeignKey(Step, on_delete=models.PROTECT)
    step_delta_ids = ChangesStepOutputs.step_delta_ids

    # override
    def load_clientside_update(self):
        data = (
            super()
            .load_clientside_update()
            .update_tab(
                self.step.tab_slug,
                step_ids=list(self.step.tab.live_steps.values_list("id", flat=True)),
            )
        )
        if self.step.is_deleted:
            data = data.clear_step(self.step.id)
        else:
            data = data.replace_step(self.step.id, self.step.to_clientside())
        return data

    @classmethod
    def affected_steps_in_tab(cls, step) -> models.Q:
        # We don't need to change self.step's delta_id: just the others.
        #
        # At the time this method is called, `step` is "deleted" (well,
        # not yet created).
        return models.Q(tab_id=step.tab_id, order__gte=step.order, is_deleted=False)

    def forward(self):
        if not self.step.last_relevant_delta_id:
            # We couldn't set self.step.last_relevant_delta_id during
            # creation because `self` (the delta in question) wasn't created.
            # Set it now, before .forward_affected_delta_ids(). After this
            # first write, this Delta should never modify it.
            self.step.last_relevant_delta_id = self.id
            self.step.save(update_fields=["last_relevant_delta_id"])

        # Move subsequent modules over to make way for this one.
        tab = self.step.tab
        tab.live_steps.filter(order__gte=self.step.order).update(order=F("order") + 1)

        self.step.is_deleted = False
        self.step.save(update_fields=["is_deleted"])

        tab.selected_step_position = self.step.order
        tab.save(update_fields=["selected_step_position"])

        self.forward_affected_delta_ids()

    def backward(self):
        self.step.is_deleted = True
        self.step.save(update_fields=["is_deleted"])

        # Move subsequent modules back to fill the gap created by deleting
        tab = self.step.tab
        tab.live_steps.filter(order__gt=self.step.order).update(order=F("order") - 1)

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

        self.backward_affected_delta_ids()

    # override
    def get_modifies_render_output(self) -> bool:
        """
        Force a render.

        Adding a module to an empty workflow, self._changed_step_versions
        will be None -- and yet we need a render!

        TODO brainstorm other solutions to the original race -- that we can't
        know this delta's ID until after we save it to the database, yet we
        need to save its own ID in self._changed_step_versions.
        """
        return True

    @classmethod
    def amend_create_kwargs(
        cls, *, workflow, tab, slug, module_id_name, position, param_values, **kwargs
    ):
        """
        Add a step to the tab.

        Raise KeyError if `module_id_name` is invalid.

        Raise RuntimeError (unrecoverable) if minio holds invalid module data.

        Raise ValueError if `param_values` do not match the module's spec.
        """
        # ensure slug is unique, or raise ValueError
        if Step.objects.filter(tab__workflow_id=workflow.id, slug=slug).count() > 0:
            raise ValueError("slug is not unique. Please pass a unique slug.")

        # raise KeyError, RuntimeError
        module_zipfile = MODULE_REGISTRY.latest(module_id_name)
        module_spec = module_zipfile.get_spec()

        # Set _all_ params (not just the user-specified ones). Our
        # dropdown-menu actions only specify the relevant params and expect us
        # to set the others to defaults.
        params = {**module_spec.default_params, **param_values}

        module_spec.get_param_schema().validate(params)  # raises ValueError

        # step starts off "deleted" and gets un-deleted in forward().
        step = tab.steps.create(
            module_id_name=module_id_name,
            order=position,
            slug=slug,
            is_deleted=True,
            params=params,
            cached_migrated_params=params,
            cached_migrated_params_module_version=module_zipfile.get_param_schema_version(),
            secrets={},
        )

        return {
            **kwargs,
            "workflow": workflow,
            "step": step,
            "step_delta_ids": cls.affected_step_delta_ids(step),
        }

    @property
    def command_description(self):
        return f"Add Step {self.step}"
