from django import template
from django.utils.safestring import mark_safe
from cjworkbench.i18n.trans import trans_html as do_trans_html
import re

register = template.Library()

trans_tag_re = re.compile(
    r"^tag_(?P<placeholder>(?P<name>[a-zA-Z]+)\d+)_(?P<attr>[a-zA-Z]+)$", re.ASCII
)
trans_tag_without_attribute_re = re.compile(
    r"^tag_(?P<placeholder>(?P<name>[a-zA-Z]+)\d+)$", re.ASCII
)
trans_param_re = re.compile(r"arg_(?P<arg>\w+)", re.ASCII)


@register.simple_tag(takes_context=True)
def trans_html(
    context, message_id, *, default, ctxt="", noop=False, comment="", **kwargs
):
    """Translate a message, supporting HTML placeholders and variables.

    The message can contain variables in the form `{var}`. Their values must be given with keys of the form `arg_{variable}`,
    e.g. for the message `"Hello {name}"`, `arg_name` is expected
    The variables can't be named as integers, i.e. `{0}` is not a valid variable name.
    
    HTML tags and their attributes must have been replaced with placeholders and the original must be provided as follows:
        - Each tag placeholder consists of the name of the tag followed by an integer, e.g. `a` becomes `a0` or `a1` etc.
          You are advised to use consecutive integers starting from 0 for each tag name, 
          i.e. you could have `a0`, then `a1`, then `span0`, then `div0`, then `span1`
        - Each attribute is provided (only once) with key `tag_{placeholder}_{attribute_name}`,
          so in order to replace `<a0>...</a0>` with `<a href="/hello" class="red small">...</a>`, 
          you need to provide `tag_a0_href="/hello"` and `tag_a0_class="red small"` 
        - Tags without attributes (for example `tag_b0`) are supported; you must map them to some value, which will be ignored
        - Tags and their attributes can't contain dashes, so data attributes are not supported
    Nested HTML tags are forbidden; in fact, at this point, the inner ones will be escaped, but you should not rely on this.
    Non-nested tags that have not been mapped in this way will be ignored; in fact, at this point, they will replaced by their escaped contents, but you should not rely on this.
    
    The locale will be taken from context.
    
    For code parsing reasons, respect the following order when passing more than one of `default`, `ctxt`, and `comment` arguments:
        `default` before `ctxt` before `comment`
    
    If `noop` is the value `True`, the translation library will not be used and you will just get `None`
    
    The `comment` argument is ignored here, it's only used in code parsing.
    
    Examples:
        - `{% trans_html "messages.hello" default="Hello" comment="This can be all caps if you really want it to be" %}` 
          Looks up `messages.hello` in the catalog for the current locale; 
          if not found, returns `"Hello"`.
          When the code is parsed, the comment and the default will be added to the message catalog.
          
        - `{% trans_html "messages.hello" default="Hello {name}" arg_name="Adam"%}` 
          looks up `messages.hello` in the catalog for the current locale and provides `"Adam"` as a value for `name`; 
          if not found, returns `"Hello Adam"`
          When the code is parsed, the default will be added to the message catalog.
          
        - `{% trans_html "messages.hello" default="Hello {name}" ctxt="dashboard" arg_name="Adam"%}` 
          looks up `messages.hello` with context `dashboard` in the catalog for the current locale and provides `"Adam"` as a value for `name`; 
          if not found, returns `"Hello Adam"`
          When the code is parsed, the context and the default will be added to the message catalog.
          
        - `{% trans_html "messages.hello" noop=True default="Hello" %}` 
          returns None
          When the code is parsed, the default will be added to the message catalog.
          
        - `{% trans_html "messages.hello" default="<span0>Hello</span0> <span1>you</span1>" tag_span0_class="red big" tag_span1_class="small yellow" tag_span1_id="you" tag_em0="" %}` 
          looks up `messages.hello` in the catalog for the current locale and replaces the placeholders with the info in `tag_*` arguments;
          for example, the default message would become `'<span class="red big">Hello</span> <span class="small yellow" id="you">you</span>'` 
          When the code is parsed, the default will be added to the message catalog.
          
        - `{% trans_html some_var default="the default" %}`
          Looks up the content of `some_var` in the catalog. If found, returns it, else returns the default.
          When the code is parsed for message extraction, this will be ignored.
    """
    if noop is True:
        return None

    params = {}
    tags = {}
    for arg in kwargs:
        match_param = trans_param_re.match(arg)
        if match_param:
            params[match_param.group("arg")] = kwargs[arg]
            continue
        match_tag = trans_tag_re.match(arg)
        if match_tag:
            placeholder = match_tag.group("placeholder")
            tag_name = match_tag.group("name")
            tag_attr = match_tag.group("attr")
            if not (placeholder in tags):
                tags[placeholder] = {"tag": tag_name, "attrs": {}}
            tags[placeholder]["attrs"][tag_attr] = kwargs[arg]
            continue
        match_tag = trans_tag_without_attribute_re.match(arg)
        if match_tag:
            placeholder = match_tag.group("placeholder")
            tag_name = match_tag.group("name")
            if not (placeholder in tags):
                tags[placeholder] = {"tag": tag_name, "attrs": {}}
            continue

    return mark_safe(
        do_trans_html(
            context["i18n"]["locale_id"],
            message_id,
            default=default,
            context=ctxt,
            tags=tags,
            parameters=params,
        )
    )
