from django import template
from django.utils.safestring import mark_safe
from cjworkbench.i18n.trans import trans as trans_icu

register = template.Library()


@register.simple_tag(takes_context=True)
def trans(
    context,
    message_id,
    default=None,
    ctxt="",
    noop=False,
    comment="",
    locale=None,
    **kwargs,
):
    """Translate a message, supporting ICU syntax.

    Keyword arguments, apart from the ones explicitly named in the signature, will be passed to the ICU message.
    The locale will be taken from request if not provided.
    
    For code parsing reasons, respect the following order when passing more than one of `default`, `ctxt`, and `comment` arguments:
        `default` before `ctxt` before `comment`
    
    If `noop` is the value `True`, the translation library will not be used and you will just get the message ID (or the default value, if it's truthy)
    
    The `comment` argument is ignored here, it's only used in code parsing.
    
    Examples:
        - `{% trans "Hello" %}` 
          Looks up `Hello` in the catalog for the current locale; 
          if not found, returns `"Hello"`
          
        - `{% trans "messages.hello" default="Hello" comment="This can be all caps if you really want it to be" %}` 
          Looks up `messages.hello` in the catalog for the current locale; 
          if not found, returns `"Hello"`.
          When the code is parsed, the comment and the default will be added to the message catalog.
          
        - `{% trans "messages.hello" default="Hello {name}" name="Adam"%}` 
          looks up `messages.hello` in the catalog for the current locale and provides `"Adam"` as a value for `name`; 
          if not found, returns `"Hello Adam"`
          When the code is parsed, the default will be added to the message catalog.
          
        - `{% trans "messages.hello" default="Hello {name}" ctxt="dashboard" name="Adam"%}` 
          looks up `messages.hello` with context `dashboard` in the catalog for the current locale and provides `"Adam"` as a value for `name`; 
          if not found, returns `"Hello Adam"`
          When the code is parsed, the context and the default will be added to the message catalog.
          
        - `{% trans "messages.hello" noop=True default="Hello" %}` 
          returns `"Hello"`
          When the code is parsed, the default will be added to the message catalog.
          
        - `{% trans some_var %}`
          Looks up the content of some_var in the catalog.
          When the code is parsed, this will be ignored.
    """
    if noop is True:
        return mark_safe(default or message_id)
    return mark_safe(
        trans_icu(
            locale or context["request"].locale_id,
            message_id,
            default=default,
            context=ctxt,
            parameters=kwargs,
        )
    )
