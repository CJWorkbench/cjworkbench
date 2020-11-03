from typing import List

from ..dbutil import reorder_list_by_slugs
from .base import BaseCommand


class ReorderBlocks(BaseCommand):
    """Overwrite block.position for all blocks in a workflow's Report.

    The user may be reordering blocks on the "auto-generated" report. If so,
    we set `values_for_backward["workflow_has_custom_report"]=False`; forward()
    creates all the blocks in the desired order.
    """

    def load_clientside_update(self, delta):
        workflow = delta.workflow
        block_slugs = list(workflow.blocks.values_list("slug", flat=True))
        ret = (
            super()
            .load_clientside_update(delta)
            .update_workflow(block_slugs=block_slugs)
        )

        if delta.values_for_backward["slugs"] is None:
            # We started with an auto-report. Create/delete every block on all clients
            if workflow.blocks.exists():
                # We're in forward(). Create all blocks.
                ret = ret.update_workflow(has_custom_report=True).replace_blocks(
                    {
                        block.slug: block.to_clientside()
                        for block in workflow.blocks.all()
                    }
                )
            else:
                # We're in backward(). Delete all blocks.
                ret = ret.update_workflow(has_custom_report=False).clear_blocks(
                    delta.values_for_forward["slugs"]
                )

        return ret

    def forward(self, delta):
        from ..reports import build_auto_report_for_workflow

        workflow = delta.workflow
        slugs = delta.values_for_forward["slugs"]

        if workflow.has_custom_report:
            reorder_list_by_slugs(workflow.blocks, "position", slugs)
        else:
            # This reorder was on an auto-report. So really, we're creating
            # the entire report here, in the specified order.
            workflow.has_custom_report = True
            workflow.save(update_fields=["has_custom_report"])
            auto_report = build_auto_report_for_workflow(workflow)
            block_lookup = {block.slug: block for block in auto_report}
            if frozenset(block_lookup.keys()) != frozenset(slugs):
                raise RuntimeError("Reorder with wrong slugs")
            for position, slug in enumerate(slugs):
                block = block_lookup[slug]
                block.position = position
                block.save()

    def backward(self, delta):
        workflow = delta.workflow
        slugs = delta.values_for_backward["slugs"]

        if slugs is None:
            # The reorder created a custom report from an auto-report. Delete.
            workflow.blocks.all().delete()
            workflow.has_custom_report = False
            workflow.save(update_fields=["has_custom_report"])
        else:
            reorder_list_by_slugs(workflow.blocks, "position", slugs)

    def amend_create_kwargs(self, *, workflow: "Workflow", new_order: List[str]):
        from ..reports import build_auto_report_for_workflow

        if workflow.has_custom_report:
            old_order = list(workflow.blocks.values_list("slug", flat=True))
            old_order_for_compare = old_order
        else:
            old_order = None
            old_order_for_compare = [
                b.slug for b in build_auto_report_for_workflow(workflow)
            ]

        if old_order_for_compare == new_order:
            return None  # no-op
        # Assume old_order_for_compare never has duplicates, because the
        # database is consistent.
        if len(old_order_for_compare) != len(new_order) or frozenset(
            old_order_for_compare
        ) != frozenset(new_order):
            raise ValueError("Wrong block slugs")

        return {
            "workflow": workflow,
            "values_for_forward": {"slugs": new_order},
            "values_for_backward": {"slugs": old_order},
        }
