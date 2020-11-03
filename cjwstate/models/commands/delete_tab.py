from django.db.models import F, Q, QuerySet

from cjwstate import clientside
from ..dbutil import make_gap_in_list, remove_gap_from_list
from .base import BaseCommand


def _blocks_q(tab: "Tab") -> QuerySet:
    from ..block import Block

    return Block.objects.filter(workflow_id=tab.workflow_id).filter(
        Q(tab_id=tab.id) | Q(step__tab_id=tab.id)
    )


class DeleteTab(BaseCommand):
    """Remove `tab` from its Workflow.

    Our logic is to "soft-delete": set `tab.is_deleted=True`. Most facets of
    Workbench's API should pretend a soft-deleted Tab does not exist.
    """

    def load_clientside_update(self, delta):
        data = (
            super()
            .load_clientside_update(delta)
            .update_workflow(
                tab_slugs=list(delta.workflow.live_tabs.values_list("slug", flat=True))
            )
        )
        if delta.tab.is_deleted:
            data = data.clear_tab(delta.tab.slug)
        else:
            data = data.replace_tab(delta.tab.slug, delta.tab.to_clientside())
        blocks = delta.values_for_backward.get("blocks", [])
        if blocks:
            data = data.update_workflow(
                block_slugs=list(delta.workflow.blocks.values_list("slug", flat=True))
            )
            if delta.tab.is_deleted:
                data = data.clear_blocks(block["slug"] for block in blocks)
            else:
                clientside_blocks = {}
                for block in blocks:
                    if block["block_type"] == "Chart":
                        clientside_block = clientside.ChartBlock(block["step_slug"])
                    else:
                        clientside_block = clientside.TableBlock(delta.tab.slug)
                    clientside_blocks[block["slug"]] = clientside_block
                data = data.replace_blocks(clientside_blocks)
        return data

    def forward(self, delta):
        delta.tab.is_deleted = True
        delta.tab.save(update_fields=["is_deleted"])

        # Delete charts and tables from the report
        blocks_q = _blocks_q(delta.tab)
        blocks = list(blocks_q)
        blocks_q.delete()
        for block in reversed(blocks):
            remove_gap_from_list(delta.workflow.blocks, "position", block.position)

        delta.workflow.live_tabs.filter(position__gt=delta.tab.position).update(
            position=F("position") - 1
        )

        if delta.workflow.selected_tab_position >= delta.tab.position:
            delta.workflow.selected_tab_position = max(
                delta.workflow.selected_tab_position - 1, 0
            )
            delta.workflow.save(update_fields=["selected_tab_position"])

    def backward(self, delta):
        delta.workflow.live_tabs.filter(position__gte=delta.tab.position).update(
            position=F("position") + 1
        )

        delta.tab.is_deleted = False
        delta.tab.save(update_fields=["is_deleted"])

        # Re-create deleted Blocks
        blocks = delta.values_for_backward.get("blocks", [])
        for block_kwargs in blocks:
            make_gap_in_list(
                delta.workflow.blocks, "position", block_kwargs["position"]
            )
            if block_kwargs["block_type"] == "Chart":
                step = delta.tab.live_steps.get(slug=block_kwargs["step_slug"])
                delta.workflow.blocks.create(
                    **{k: v for k, v in block_kwargs.items() if k != "step_slug"},
                    step_id=step.id,
                )
            elif block_kwargs["block_type"] == "Table":
                delta.workflow.blocks.create(**block_kwargs, tab_id=delta.tab.id)
            else:
                raise NotImplementedError

        # Focus the un-deleted tab -- because why not
        delta.workflow.selected_tab_position = delta.tab.position
        delta.workflow.save(update_fields=["selected_tab_position"])

    def amend_create_kwargs(self, *, workflow: "Workflow", tab: "Tab"):
        if tab.is_deleted:
            return None  # no-op: something raced

        if workflow.live_tabs.count() == 1:
            return None  # no-op: we cannot delete the last tab

        values_for_backward = {}
        if workflow.has_custom_report:
            values_for_backward["blocks"] = list(
                {
                    k: v
                    for k, v in block.to_json_safe_kwargs().items()
                    if k != "tab_slug"
                }
                for block in _blocks_q(tab)
            )

        return {
            "workflow": workflow,
            "tab": tab,
            "values_for_backward": values_for_backward,
        }
