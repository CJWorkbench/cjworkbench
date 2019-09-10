from django import template
from i18n.trans import trans as trans_icu

register = template.Library()

@register.simple_tag(takes_context=True)
def trans(context, message_id, default=None, locale=None, **kwargs):
    """Translate a message, supporting ICU syntax.

    The locale will be taken from request if not provided.
    Named arguments, apart from default and locale, will be passed to the ICU message.
    """
    return trans_icu(
        locale or context["request"].locale_id,
        message_id,
        default=default,
        parameters=kwargs,
    )
