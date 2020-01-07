from bs4 import BeautifulSoup
from django.utils.functional import lazy
from django.utils.html import escape
from django.utils.translation import get_language
from cjworkbench.i18n import default_locale
from cjworkbench.i18n.catalogs import load_catalog
from string import Formatter
from cjworkbench.i18n.exceptions import UnsupportedLocaleError, BadCatalogsError
from icu import (
    Formattable,
    Locale,
    MessageFormat,
    UnicodeString,
    ResourceBundle,
    ICUError,
)


class InvalidICUParameters(Exception):
    """The parameters passed for a message are not valid
    
    For example, you may have passed a string in the place of an integer.
    """


_translators = {}


def _get_translations(locale):
    """Return a singleton MessageTranslator for the given locale.
    
    In order to parse the message catalogs only once per locale,
    uses the _translators dict to store the created MessageTranslator for each locale.
    """
    if locale in _translators:
        return _translators[locale]
    _translators[locale] = MessageTranslator(locale)
    return _translators[locale]


def trans(message_id, *, default, context=None, parameters={}):
    """Translate the given message ID to the current locale
    
    HTML is not escaped.
    
    For code parsing reasons, respect the following order when passing keyword arguments:
        `message_id` and then `default` and then `context` and then everything else
    """
    return do_trans(
        get_language(),
        message_id,
        default=default,
        context=context,
        parameters=parameters,
    )


def do_trans(locale_id, message_id, *, default, context=None, parameters={}):
    """Translate the given message ID to the given locale
    
    HTML is not escaped.
    
    For code parsing reasons, respect the following order when passing keyword arguments:
        `message_id` and then `default` and then `context` and then everything else
    """
    return _get_translations(locale_id).trans(
        message_id, default=default, context=context, parameters=parameters
    )


def trans_html(locale, message_id, *, default, context=None, parameters={}, tags={}):
    """Translate the given message ID to the current locale
    
    HTML is escaped in the message, as well as in parameters and tag attributes.
    
    For code parsing reasons, respect the following order when passing keyword arguments:
        `message_id` and then `default` and then `context` and then everything else
    """
    return _get_translations(locale).trans_html(
        message_id, default=default, context=context, parameters=parameters, tags=tags
    )


trans_lazy = lazy(trans)
"""Mark a string for translation, but actually translate it when it has to be used.
   See the documentation of `trans` for more details on the parameters.
"""


def restore_tags(message, tag_mapping):
    """Replace the HTML tags and attributes in a message.
    
    `tag_mapping` is a dict that for each tag name contains a new name `name` and new attributes `attrs`
    
    For each non-nested HTML tag found, searches `tag_mapping` for a replacement for its name and attributes.
    If found, replaces with the ones found.
    If not found, removes the tag but keeps the (escaped) contents.
    
    Nested HTML tags are removed, with their (escaped) contents kept
    
    Returns the new message
    """
    soup = BeautifulSoup(message, "html.parser")
    bad = []
    for child in soup.children:
        if child.name:  # i.e. child is a tag
            if child.name in tag_mapping:
                child.attrs = tag_mapping[child.name].get("attrs", {})
                child.name = tag_mapping[child.name]["tag"]
                child.string = "".join(child.strings)
            else:
                bad.append(child)
    for child in bad:
        child.string = escape("".join(child.strings))
        child.unwrap()
    return str(soup)


class MessageTranslator:
    """Load the message catalogs for a given locale and provide helper methods for message translation.
    It uses plaintext messages with variables in `{var}` placeholders, e.g. in `"Hello {name}"`, `name` is a variable.
    
    Essentially, it is a wrapper for the combination of 
      - Babel (for loading PO files)
      - variable substitution
      - our HTML placeholder construct.
    """

    def __init__(self, locale):
        self.locale = locale
        self.catalog = load_catalog(locale)

    def trans(self, message_id, default=None, context=None, parameters={}):
        """Find the message corresponding to the given ID in the catalog and format it according to the given parameters.
        If the message is either not found or empty and a non-empty `default` is provided, the `default` is used instead.
        
        See `self._format_message` for acceptable types of the parameters argument.
        
        In case a message from the catalogs is used, if the message contains illegal (i.e. numeric) variables, 
        they are handled so as to not raise an exception; at this point, the default message is used instead, but you should not rely on this behaviour
        """
        return self._process_simple_message(
            self.get_message(message_id, context=context),
            default or message_id,
            parameters,
        )

    def trans_html(
        self, message_id, default=None, context=None, parameters={}, tags={}
    ):
        """Find the message corresponding to the given ID in the catalog and format it according to the given parameters.
        If the message is either not found or empty and a non-empty `default` is provided, the `default` is used instead.
        
        See `self._format_message` for acceptable types of the parameters argument.
        
        In case a message from the catalogs is used, if the message contains illegal (i.e. numeric) variables, 
        they are handled so as to not raise an exception; at this point, the default message is used instead, but you should not rely on this behaviour
        
        HTML-like tags in the message used are replaced by their counterpart in `tags`, as specified in `restore_tags`
        """
        return self._process_html_message(
            self.get_message(message_id, context=context),
            default or message_id,
            parameters,
            tags,
        )

    def _process_simple_message(self, message, fallback, parameters={}):
        if message:
            try:
                return self._format_message(
                    message, parameters=parameters, do_escape=False
                )
            except (ICUError, InvalidICUParameters):
                pass
        return self._format_message(fallback, parameters=parameters, do_escape=False)

    def _process_html_message(self, message, fallback, parameters={}, tags={}):
        if message:
            try:
                return self._format_message(
                    self._replace_tags(message, tags),
                    parameters=parameters,
                    do_escape=True,
                )
            except (ICUError, InvalidICUParameters):
                pass
        return self._format_message(
            self._replace_tags(fallback, tags), parameters=parameters, do_escape=True
        )

    def _replace_tags(self, target_message, tags):
        """Replace non-nested tag names and attributes of the `target_message` with the corresponding ones in `tags`
        
        `tags` must be a dict that maps each placeholder in `target_message` to its original tag and attrs,
        e.g. a message like `"Click <a0>here</a0>"` expects tags like `{'a0': {'tag': 'a', 'attrs': {'href': 'http://example.com/pages/1'}}}`
        """
        return restore_tags(target_message, tag_mapping=tags)

    def _format_message(self, message, parameters={}, do_escape=True):
        """Substitute parameters into ICU-style message.
        You can have variable substitution, plurals, selects and nested messages.
        
        The parameters must be a dict
        """
        if not message:
            return message
        message_format = MessageFormat(
            UnicodeString(message), Locale.createFromName(self.locale)
        )
        if isinstance(parameters, dict):
            try:
                return message_format.format(
                    [UnicodeString(x) for x in list(parameters.keys())],
                    [
                        Formattable(
                            escape(x) if do_escape and isinstance(x, str) else x
                        )
                        for x in list(parameters.values())
                    ],
                )
            except Exception as error:
                raise InvalidICUParameters(
                    "The given parameters are invalid for the given message"
                ) from error
        else:
            raise InvalidICUParameters("The given parameters are not a dict") from error

    def get_message(self, message_id, context=None):
        """Find the message corresponding to the given ID in the catalog.
        
        If the message is not found, `None` is returned.
        """
        if context:
            message = self.catalog.get(message_id, context)
        else:
            message = self.catalog.get(message_id)
        return message.string if message else None
