from django.db.models import Q

from cjwstate import clientside
from cjwstate.models.module_registry import MODULE_REGISTRY
from ..dbutil import make_gap_in_list, remove_gap_from_list
from .base import BaseCommand
from .util import ChangesStepOutputs


class ReplaceStep(ChangesStepOutputs, BaseCommand):
    """Create a `Step` and delete another.

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
        blocks = delta.values_for_backward.get("blocks", [])
        if blocks:
            data = data.update_workflow(
                block_slugs=list(delta.workflow.blocks.values_list("slug", flat=True))
            )
            if delta.step.is_deleted:
                # Clear the blocks we deleted
                data = data.clear_blocks(block["slug"] for block in blocks)
            else:
                # Undoing, we need to re-add slugs
                data = data.replace_blocks(
                    {
                        block["slug"]: clientside.ChartBlock(delta.step.slug)
                        for block in blocks
                    }
                )
        if delta.step.is_deleted:
            deleted_step = delta.step
            added_step = delta.step2
        else:
            deleted_step = delta.step2
            added_step = delta.step
        data = data.clear_step(deleted_step.id).replace_step(
            added_step.id, added_step.to_clientside()
        )
        return data

    # override
    def affected_steps_in_tab(self, step) -> Q:
        # We don't need to change self.step or self.step2's delta_id: just the
        # successors'.
        return Q(tab_id=step.tab_id, order__gt=step.order, is_deleted=False)

    def forward(self, delta):
        if not delta.step2.last_relevant_delta_id:
            # We couldn't set step2.last_relevant_delta_id during Delta creation
            # because `delta` didn't exist at that point.
            # Set it now, before .forward_affected_delta_ids(). After this
            # first write, this Delta should never modify it.
            delta.step2.last_relevant_delta_id = delta.id
            delta.step2.save(update_fields=["last_relevant_delta_id"])

        # Delete charts from the report
        blocks = list(delta.step.blocks.all())
        delta.step.blocks.all().delete()
        for block in reversed(blocks):
            remove_gap_from_list(delta.workflow.blocks, "position", block.position)

        delta.step.is_deleted = True
        delta.step.save(update_fields=["is_deleted"])

        delta.step2.is_deleted = False
        delta.step2.save(update_fields=["is_deleted"])

        tab = delta.step2.tab
        tab.selected_step_position = delta.step2.order
        tab.save(update_fields=["selected_step_position"])

        self.forward_affected_delta_ids(delta)

    def backward(self, delta):
        delta.step2.is_deleted = True
        delta.step2.save(update_fields=["is_deleted"])

        delta.step.is_deleted = False
        delta.step.save(update_fields=["is_deleted"])

        tab = delta.step.tab
        tab.selected_step_position = delta.step.order
        tab.save(update_fields=["selected_step_position"])

        blocks = delta.values_for_backward.get("blocks", [])
        for block_kwargs in blocks:
            make_gap_in_list(
                delta.workflow.blocks, "position", block_kwargs["position"]
            )
            delta.workflow.blocks.create(**block_kwargs, step_id=delta.step_id)

        self.backward_affected_delta_ids(delta)

    # override
    def get_modifies_render_output(self, delta) -> bool:
        """Force a render.

        When replacing the last module, `delta._changed_step_versions` will be
        empty -- and yet we need a render.
        """
        return True

    def amend_create_kwargs(
        self, *, workflow, old_slug, slug, module_id_name, param_values, **kwargs
    ):
        """Delete `step` and add a new step with `slug` in its stead.

        No-op if `old_slug` does not exist in `workflow`.

        Raise KeyError if `module_id_name` is invalid.

        Raise RuntimeError (unrecoverable) if s3 holds invalid module data.

        Raise ValueError if `param_values` do not match the module's spec.
        """
        from ..step import Step

        # If step is already deleted, ignore this Delta.
        #
        # This works around a race: what if two users delete the same Step
        # at the same time? We want only one Delta to be created.
        # amend_create_kwargs() is called within workflow.cooperative_lock(),
        # so we can check without racing whether step is already deleted.
        try:
            step = Step.live_in_workflow(workflow).get(slug=old_slug)
        except Step.DoesNotExist:
            return None

        # ensure slug is unique, or raise ValueError
        if Step.objects.filter(tab__workflow_id=workflow.id, slug=slug).exists():
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
        step2 = step.tab.steps.create(
            module_id_name=module_id_name,
            order=step.order,
            slug=slug,
            is_deleted=True,
            params=params,
            cached_migrated_params=params,
            cached_migrated_params_module_version=module_zipfile.version,
            secrets={},
        )

        values_for_backward = {}
        if workflow.has_custom_report:
            values_for_backward["blocks"] = list(
                {
                    k: v
                    for k, v in block.to_json_safe_kwargs().items()
                    if k != "step_slug"
                }
                for block in step.blocks.all()
            )

        return {
            **kwargs,
            "workflow": workflow,
            "step": step,
            "step2": step2,
            "step_delta_ids": self.affected_step_delta_ids(step),
            "values_for_backward": values_for_backward,
        }
