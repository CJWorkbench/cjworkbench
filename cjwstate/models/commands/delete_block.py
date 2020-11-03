from .base import BaseCommand
from ..reports import build_auto_report_for_workflow
from ..dbutil import make_gap_in_list, remove_gap_from_list


class DeleteBlock(BaseCommand):
    """Remove a `Block` from the Workflow's Report.

    The user may be removing a Block from the "auto-generated" report. If so,
    we set `values_for_backward["workflow_has_custom_report"]=False`; forward()
    creates all the blocks but one and sets workflow.has_custom_report=True.
    """

    def load_clientside_update(self, delta):
        workflow = delta.workflow
        slug = delta.values_for_forward["slug"]
        auto_report_block_slugs = delta.values_for_backward["auto_report_block_slugs"]
        block_kwargs = delta.values_for_backward["block"]
        block_slugs = list(workflow.blocks.values_list("slug", flat=True))

        ret = (
            super()
            .load_clientside_update(delta)
            .update_workflow(block_slugs=block_slugs)
        )

        if block_kwargs is None:
            # This is a "delete-from-auto-report"
            if workflow.has_custom_report:
                # We're in forward(). We created a whole custom report.
                ret = ret.update_workflow(has_custom_report=True).replace_blocks(
                    {
                        block.slug: block.to_clientside()
                        for block in workflow.blocks.all()
                    }
                )
            else:
                # We're in backward(). The custom report is gone.
                ret = ret.update_workflow(has_custom_report=False).clear_blocks(
                    auto_report_block_slugs
                )
        else:
            # This is a regular "delete a single block" command
            block = workflow.blocks.filter(slug=slug).first()
            if block is None:
                # We're in forward(). The block is gone.
                ret = ret.clear_blocks([slug])
            else:
                # We're in backward(). The block is back.
                ret = ret.replace_blocks({block.slug: block.to_clientside()})

        return ret

    def forward(self, delta):
        from ..reports import build_auto_report_for_workflow

        workflow = delta.workflow
        slug = delta.values_for_forward["slug"]

        if workflow.has_custom_report:
            # Delete the one block
            block = workflow.blocks.get(slug=slug)
            block.delete()
            remove_gap_from_list(workflow.blocks, "position", block.position)
        else:
            # Build the custom report -- all but the deleted slug
            workflow.has_custom_report = True
            workflow.save(update_fields=["has_custom_report"])

            blocks = build_auto_report_for_workflow(workflow)
            for block in blocks:
                if block.slug == slug:
                    blocks.remove(block)
                    break
            else:
                raise RuntimeError(
                    "Could not find auto-block slug"
                )  # should never happen
            for i, block in enumerate(blocks):
                block.position = i
                block.save()

    def backward(self, delta):
        from ..block import Block

        workflow = delta.workflow
        block_kwargs = delta.values_for_backward["block"]

        if block_kwargs is None:
            # The block didn't exist when we called forward(), because we
            # started with an auto-report. Revert to auto-report.
            workflow.blocks.all().delete()
            workflow.has_custom_report = False
            workflow.save(update_fields=["has_custom_report"])
        else:
            # Put the block back where we found it
            make_gap_in_list(workflow.blocks, "position", block_kwargs["position"])
            workflow.blocks.create(**block_kwargs)

    def amend_create_kwargs(self, *, workflow: "Workflow", slug: str):
        from ..step import Step
        from ..reports import build_auto_report_for_workflow

        if workflow.has_custom_report:
            auto_report_block_slugs = None
            block = workflow.blocks.get(slug=slug)  # raises Block.DoesNotExist
        else:
            auto_report_block_slugs = list(
                block.slug for block in build_auto_report_for_workflow(workflow)
            )
            try:
                auto_report_block_slugs.remove(slug)  # raise ValueError
            except ValueError:
                raise ValueError("There is no auto-block with this slug") from None
            block = None

        return {
            "workflow": workflow,
            "values_for_forward": {"slug": slug},
            "values_for_backward": {
                "auto_report_block_slugs": auto_report_block_slugs,
                "block": None if block is None else block.to_json_safe_kwargs(),
            },
        }
