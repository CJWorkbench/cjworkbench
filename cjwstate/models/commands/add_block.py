from typing import Literal, Optional

from cjwstate import clientside
from ..dbutil import make_gap_in_list, remove_gap_from_list
from .base import BaseCommand


class AddBlock(BaseCommand):
    """Create a `Block` and insert it into the Workflow's Report.

    The user may be adding a Block to the "auto-generated" report. If so,
    we set `values_for_backward["workflow_has_custom_report"]=False`; forward
    creates all the blocks and sets workflow.has_custom_report=True.
    """

    def load_clientside_update(self, delta):
        workflow = delta.workflow

        ret = (
            super()
            .load_clientside_update(delta)
            .update_workflow(
                block_slugs=list(workflow.blocks.values_list("slug", flat=True))
            )
        )

        if delta.values_for_backward["auto_report_block_slugs"] is None:
            # It was a custom report before, and it's still a custom report. We
            # added/removed a single block.
            block_slug = delta.values_for_forward["block"]["slug"]
            block = workflow.blocks.filter(slug=block_slug).first()
            if block:
                # forward() - we created the block
                ret = ret.replace_blocks({block_slug: block.to_clientside()})
            else:
                # backward() - we deleted the block
                ret = ret.clear_blocks([block_slug])
        else:
            # It _was_ an auto-report, and now it's a custom report. We
            # added/remove all blocks in the workflow.
            blocks = list(workflow.blocks.all())
            if blocks:
                # forward() - we created all blocks
                ret = ret.update_workflow(has_custom_report=True).replace_blocks(
                    {block.slug: block.to_clientside() for block in blocks}
                )
            else:
                # backward() - we deleted all blocks
                ret = ret.update_workflow(has_custom_report=False).clear_blocks(
                    delta.values_for_backward["auto_report_block_slugs"]
                    + [delta.values_for_forward["block"]["slug"]]
                )

        return ret

    def forward(self, delta):
        workflow = delta.workflow

        if not workflow.has_custom_report:
            from ..reports import build_auto_report_for_workflow

            workflow.has_custom_report = False
            workflow.save(update_fields=["has_custom_report"])
            auto_report = build_auto_report_for_workflow(workflow)
            for auto_block in auto_report:
                auto_block.save()

        block_kwargs = delta.values_for_forward["block"]
        make_gap_in_list(workflow.blocks, "position", block_kwargs["position"])
        workflow.blocks.create(**block_kwargs)

    def backward(self, delta):
        workflow = delta.workflow

        if delta.values_for_backward["auto_report_block_slugs"] is None:
            # forward() added to a custom report. Delete the added block.
            block_slug = delta.values_for_forward["block"]["slug"]
            block = workflow.blocks.get(slug=block_slug)
            block.delete()
            remove_gap_from_list(workflow.blocks, "position", block.position)
        else:
            # forward() built an auto-report. Now we delete it.
            workflow.blocks.all().delete()
            workflow.has_custom_report = False
            workflow.save(update_fields=["has_custom_report"])

    def amend_create_kwargs(
        self,
        *,
        workflow: "Workflow",
        position: int,
        slug: str,
        block_type: Literal["Chart", "Text", "Table"],
        step_slug: Optional[str] = None,
        tab_slug: Optional[str] = None,
        text_markdown: str = "",
    ):
        from ..step import Step
        from ..reports import build_auto_report_for_workflow

        block = {
            "slug": slug,
            "position": position,
            "block_type": block_type,
        }
        if block_type == "Text":
            if text_markdown == "" or step_slug is not None or tab_slug is not None:
                raise ValueError("Invalid Text params")
            block["text_markdown"] = text_markdown
        elif block_type == "Chart":
            if (
                text_markdown
                or tab_slug is not None
                or not Step.live_in_workflow(workflow).filter(slug=step_slug).exists()
            ):
                raise ValueError("Invalid Chart params")
            block["step_slug"] = step_slug
        elif block_type == "Table":
            if (
                text_markdown
                or step_slug is not None
                or not workflow.live_tabs.filter(slug=tab_slug).exists()
            ):
                raise ValueError("Invalid Table params")
            block["tab_slug"] = tab_slug

        if workflow.has_custom_report:
            auto_report_block_slugs = None
        else:
            auto_report = build_auto_report_for_workflow(workflow)
            auto_report_block_slugs = list(block.slug for block in auto_report)

        return {
            "workflow": workflow,
            "values_for_forward": {"block": block},
            "values_for_backward": {"auto_report_block_slugs": auto_report_block_slugs},
        }
