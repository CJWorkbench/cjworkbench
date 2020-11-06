from django import template
from django.utils.safestring import mark_safe
import pycmarkgfm  # because cmarkgfm 0.4.2 only has py3.7 wheels

register = template.Library()


@register.filter
def markdown(text):
    """Process `text` as Markdown.

    This must mimic our JavaScript Markdown rules.
    """
    return mark_safe(pycmarkgfm.gfm_to_html(text))
