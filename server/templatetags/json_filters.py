from django import template
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.safestring import mark_safe
import re

register = template.Library()

potential_hack_chars = re.compile('[<>&]')
def escape_potential_hack_char(m):
    c = m.group(0)

    if   c == '<': return '\\u003c'
    elif c == '<': return '\\u003e'
    elif c == '&': return '\\u0026'
    else: return c # should never happen


@register.filter
def json_in_script_tag(serialized_data):
    """Convert serialized data to HTML <script>-safe JSON.

    Example usage:

        <script>
            window.foo = {{foo|json_serialized_data}}
        </script>

    To render, we:

        1. JSON-encode, using Django's default encoder (to encode
           datetime as string, for instance).
        2. Replace `<` with `\u003c`, to prevent injection of `</script>` in
           the JSON.
    """
    raw = DjangoJSONEncoder().encode(serialized_data)
    escaped = potential_hack_chars.sub(escape_potential_hack_char, raw)
    return mark_safe(escaped)
