from django import template
from django.utils.safestring import mark_safe
from cjworkbench.i18n.trans import trans as trans_icu
from ast import literal_eval

register = template.Library()


@register.simple_tag(takes_context=True)
def trans(
    context,
    message_id,
    default=None,
    tags="{}",
    ctxt="",
    noop=False,
    comment="",
    locale=None,
    **kwargs,
):
    """Translate a message, supporting variables in the form `{var}`.

    Keyword arguments, apart from the ones explicitly named in the signature, will be used for variable substitution.
    The locale will be taken from request if not provided.
    
    HTML tags and their attributes must have been replaced with placeholders and the original must be provided in the `tags` argument.
    Nested HTML tags are forbidden.
    
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
          
        - `{% trans "messages.hello" default="<span0>Hello</span0> <span1>you</span1>" tags={'span0': {'tag': 'span', 'attrs': {'class': 'red big'}}, 'span1': {'tag': 'span', 'attrs': {'class': 'small yellow', 'id': 'you'}}} %}` 
          looks up `messages.hello` in the catalog for the current locale and replaces the placeholders with the info in `tags`;
          for example, the default message would become `'<span class="red big">Hello</span> <span class="small yellow" id="you">you</span>'` 
          When the code is parsed, the default will be added to the message catalog.
          
        - `{% trans some_var %}`
          Looks up the content of some_var in the catalog.
          When the code is parsed, this will be ignored.
    """
    if noop is True:
        return mark_safe(default or message_id)
    tags = literal_eval(tags)
    return mark_safe(
        trans_icu(
            locale or context["request"].locale_id,
            message_id,
            default=default,
            context=ctxt,
            tags=tags,
            parameters=kwargs,
        )
    )


@register.filter
def addstr(arg1, arg2):
    """concatenate arg1 & arg2"""
    return str(arg1) + str(arg2)
