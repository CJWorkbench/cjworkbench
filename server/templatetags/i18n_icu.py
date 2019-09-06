from django import template
from i18n.trans import get_translations

register = template.Library()

@register.simple_tag(takes_context=True)
def trans(context, message_id, default=None, locale=None, **kwargs):
    """Translate a message, supporting ICU syntax.

    The locale will be taken from request if not provided.
    The named arguments, apart from default and locale, will be passed to the ICU message.
    """
    return get_translations(locale or context['request'].locale_id)._(message_id, default=default, parameters=kwargs)
