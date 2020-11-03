from .base import BaseCommand


class SetBlockMarkdown(BaseCommand):
    """Overwrite a Block's .text_markdown in a workflow's Report."""

    def load_clientside_update(self, delta):
        slug = delta.values_for_forward["slug"]
        block = delta.workflow.blocks.get(slug=slug)

        return (
            super()
            .load_clientside_update(delta)
            .replace_blocks({block.slug: block.to_clientside()})
        )

    def forward(self, delta):
        slug = delta.values_for_forward["slug"]
        markdown = delta.values_for_forward["markdown"]
        delta.workflow.blocks.filter(slug=slug).update(text_markdown=markdown)

    def backward(self, delta):
        slug = delta.values_for_forward["slug"]
        markdown = delta.values_for_backward["markdown"]
        delta.workflow.blocks.filter(slug=slug).update(text_markdown=markdown)

    def amend_create_kwargs(self, *, workflow: "Workflow", slug: str, markdown: str):
        if not markdown:
            raise ValueError("Cannot set to the empty string")
        block = workflow.blocks.get(
            slug=slug, block_type="Text"
        )  # raise Block.DoesNotExist
        if block.text_markdown == markdown:
            return None  # no-op

        return {
            "workflow": workflow,
            "values_for_forward": {"slug": slug, "markdown": markdown},
            "values_for_backward": {"markdown": block.text_markdown},
        }
