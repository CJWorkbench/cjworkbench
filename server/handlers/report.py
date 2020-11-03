import re
from typing import List, Literal, Optional

from cjwstate import commands
from cjwstate.models.block import Block
from cjwstate.models.commands.add_block import AddBlock
from cjwstate.models.commands.delete_block import DeleteBlock
from cjwstate.models.commands.reorder_blocks import ReorderBlocks
from cjwstate.models.commands.set_block_markdown import SetBlockMarkdown
from cjwstate.models.workflow import Workflow

from .decorators import register_websockets_handler, websockets_handler
from .types import HandlerError


SlugRegex = re.compile(r"\A[-a-zA-Z0-9_]+\Z")


def _parse_slug(slug: str):
    """Return `slug` or raise HandlerError."""
    slug = str(slug)  # cannot error from JSON params
    if not SlugRegex.match(slug):
        raise HandlerError(
            f'BadRequest: slug must match regex "[-a-zA-Z0-9_]+"; got "{slug}"'
        )
    return slug


@register_websockets_handler
@websockets_handler("write")
async def add_block(
    workflow: Workflow,
    slug: str,
    position: int,
    blockType: Literal["Chart", "Table", "Text"],
    tabSlug: Optional[str] = None,
    stepSlug: Optional[str] = None,
    markdown: str = "",
    **kwargs,
):
    slug = _parse_slug(slug)
    if not isinstance(position, int):
        raise HandlerError("BadRequest: position must be int")
    if blockType not in {"Chart", "Table", "Text"}:
        raise HandlerError("BadRequest: blockType must be Chart, Table or Text")
    if tabSlug is not None and not isinstance(tabSlug, str):
        raise HandlerError("BadRequest: tabSlug must be str")
    if stepSlug is not None and not isinstance(stepSlug, str):
        raise HandlerError("BadRequest: stepSlug must be str")
    if not isinstance(markdown, str):
        raise HandlerError("BadRequest: markdown must be str")

    try:
        await commands.do(
            AddBlock,
            workflow_id=workflow.id,
            slug=slug,
            position=position,
            block_type=blockType,
            tab_slug=tabSlug,
            step_slug=stepSlug,
            text_markdown=markdown,
        )
    except ValueError as err:
        raise HandlerError("%s: %s" % (type(err).__name__, str(err)))


@register_websockets_handler
@websockets_handler("write")
async def delete_block(workflow: Workflow, slug: str, **kwargs):
    slug = _parse_slug(slug)

    try:
        await commands.do(DeleteBlock, workflow_id=workflow.id, slug=slug)
    except (Block.DoesNotExist, ValueError) as err:
        raise HandlerError("%s: %s" % (type(err).__name__, str(err)))


@register_websockets_handler
@websockets_handler("write")
async def reorder_blocks(workflow: Workflow, slugs: List[str], **kwargs):
    if not isinstance(slugs, list):
        raise HandlerError("BadRequest: slugs must be an Array")
    slugs = [_parse_slug(slug) for slug in slugs]

    try:
        await commands.do(ReorderBlocks, workflow_id=workflow.id, slugs=slugs)
    except ValueError as err:
        raise HandlerError("%s: %s" % (type(err).__name__, str(err)))


@register_websockets_handler
@websockets_handler("write")
async def set_block_markdown(workflow: Workflow, slug: str, markdown: str, **kwargs):
    slug = _parse_slug(slug)
    if not isinstance(markdown, str):
        raise HandlerError("BadRequest: markdown must be a String")

    try:
        await commands.do(
            SetBlockMarkdown, workflow_id=workflow.id, slug=slug, markdown=markdown
        )
    except (Block.DoesNotExist, ValueError) as err:
        raise HandlerError("%s: %s" % (type(err).__name__, str(err)))
