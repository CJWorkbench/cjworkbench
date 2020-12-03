import functools
import re
from pathlib import Path

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

XML_DECLARATION_PATTERN = re.compile("<\?xml[^?]*\?>")
SVG_WIDTH_STRIPPER = re.compile("<svg([^>]+)width=[\"'][^\"']+[\"']([^>]*)")
SVG_HEIGHT_STRIPPER = re.compile("(<svg[^>]+)height=[\"'][^\"']+[\"']([^>]*)")
SVG_VIEWBOX_FINDER = re.compile(
    "<svg[^>]+viewBox=[\"']\\s*0[,\\s]+0[,\\s]+32[,\\s]+32\\s*[\"']"
)
SVG_ATTR_STRIPPER = re.compile("(?:fill|stroke|stroke-width)=[\"'][^\"']+[\"']")


@functools.lru_cache
def load_svg_icon(name):
    path = Path(__file__).parent.parent.parent / "assets" / "icons" / name
    svg = path.read_text()
    viewbox = SVG_VIEWBOX_FINDER.search(svg)
    if not viewbox:
        raise ValueError(
            "SVG %s does not have viewBox=0,0,32,32. Got: %s" % (name, svg)
        )
    svg = XML_DECLARATION_PATTERN.sub("", svg)
    svg = SVG_WIDTH_STRIPPER.sub(r"\1\2", svg)
    svg = SVG_HEIGHT_STRIPPER.sub(r"\1\2", svg)
    svg = SVG_ATTR_STRIPPER.sub("", svg)
    svg = svg.replace("<svg", '<svg width="1em" height="1em" fill="currentColor"')
    return svg


@register.simple_tag(name="svg_icon")
def svg_icon(name):
    """Embed SVG directly in the HTML, with width=1em and height=1em.

    Requirements:

        * The SVG must have a viewBox of 0 0 32 32

    Mutations this function performs:

        * Deletes the <?xml ?> declaration
        * Overrides width and height to be 1em
        * Sets the SVG's fill to be "currentColor"
        * Overrides every SVG attribute
    """
    plain_name = name + ""  # PosixPath + SafeText would give TypeError
    return mark_safe(load_svg_icon(plain_name))
