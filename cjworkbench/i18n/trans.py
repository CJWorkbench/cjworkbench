from bs4 import BeautifulSoup
from django.utils.functional import lazy
from django.utils.html import escape
from django.utils.translation import get_language
from cjworkbench.i18n import default_locale, supported_locales
from cjworkbench.i18n.catalogs import load_catalog
from cjworkbench.i18n.catalogs.util import find_string
from string import Formatter
from cjworkbench.i18n.exceptions import UnsupportedLocaleError, BadCatalogsError
from icu import Formattable, Locale, MessageFormat, ICUError
from babel.messages.catalog import Catalog, Message
from typing import Dict, Union, Optional
import logging
from functools import lru_cache


_translators = {}


logger = logging.getLogger(__name__)


_TagAttributes = Dict[str, str]
""" Each attribute name is mapped to its value
"""
_Tag = Dict[str, Union[str, _TagAttributes]]
""" Has two keys: 'name': str, and 'attrs': _TagAttributes. 'attrs' is optional
"""
# We can define `_Tag` more precisely in python 3.8 used a `TypedDict`
_TagMapping = Dict[str, _Tag]
""" Maps each tag to its data
"""

_MessageArguments = Dict[str, Union[int, float, str]]


def trans(message_id: str, *, default: str, arguments: _MessageArguments = {}) -> str:
    """Mark a message for translation and localize it to the current locale.

    `default` is only considered when parsing code for message extraction.
    If the message is not found in the catalog for the current or the default locale, return `None`,
    raise `KeyError`.
    
    For code parsing reasons, respect the following order when passing keyword arguments:
        `message_id` and then `default` and then everything else
    """
    return localize(get_language(), message_id, arguments=arguments)


trans_lazy = lazy(trans)
"""Mark a string for translation, but actually localize it when it has to be used.
   See the documentation of `trans` for more details on the function and its arguments.
"""


def localize(locale_id: str, message_id: str, arguments: _MessageArguments = {}) -> str:
    """Localize the given message ID to the given locale.

    Raise `KeyError` if the message is not found (neither in the catalogs of the given and of the default locale).
    Raise `ICUError` if the message in the default locale is incorrectly formatted.
    """

    if locale_id != default_locale:
        try:
            return _get_translations(locale_id).get_and_format_message(
                message_id, arguments=arguments
            )
        except ICUError as err:
            logger.exception(
                f"Error in po file for locale {locale_id} and message {message_id}: {err}"
            )
        except KeyError as err:
            pass
    return _get_translations(default_locale).get_and_format_message(
        message_id, arguments=arguments
    )


def localize_html(
    locale_id: str,
    message_id: str,
    context: Optional[str] = None,
    arguments: _MessageArguments = {},
    tags: _TagMapping = {},
) -> str:
    """Localize the given message ID to the given locale, escaping HTML.
    
    Raise `KeyError` if the message is not found (neither in the catalogs of the given and of the default locale).
    Raise `ICUError` if the message in the default locale is incorrectly formatted.
    
    HTML is escaped in the message, as well as in arguments and tag attributes.
    """
    if locale_id != default_locale:
        try:
            return _get_translations(locale_id).get_and_format_html_message(
                message_id, context=context, arguments=arguments, tags=tags
            )
        except ICUError as err:
            logger.exception(
                f"Error in po file for locale {locale_id} and message {message_id}: {err}"
            )
        except KeyError as err:
            pass
    return _get_translations(default_locale).get_and_format_html_message(
        message_id, context=context, arguments=arguments, tags=tags
    )


def restore_tags(message: str, tag_mapping: _TagMapping) -> str:
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
    """Hold a message catalog for a given locale and provide helper methods for message localization with ICU.
    It uses plaintext messages with variables in `{var}` placeholders, e.g. in `"Hello {name}"`, `name` is a variable.
    
    Essentially, it is a wrapper for the combination of 
      - Babel (for reading messages of PO files)
      - variable substitution with ICU
      - our HTML placeholder construct.
    """

    def __init__(self, locale_id: str, catalog: Catalog):
        self.icu_locale = Locale.createFromName(locale_id)
        self.catalog = catalog

    @classmethod
    def for_application_messages(cls, locale_id: str):
        return cls(locale_id, load_catalog(locale_id))

    def get_and_format_message(
        self,
        message_id: str,
        context: Optional[str] = None,
        arguments: _MessageArguments = {},
    ) -> str:
        """Find the message corresponding to the given ID in the catalog and format it according to the given arguments.
        If the message is either not found or empty, a `KeyError` is raised.
        If the message is incorrectly formatted, an `ICUError` is raised.
        
        See `self._format_message` for acceptable types of the `arguments` argument.
        """
        return self._process_simple_message(
            self.get_message(message_id, context=context), arguments
        )

    def get_and_format_html_message(
        self,
        message_id: str,
        context: Optional[str] = None,
        arguments: _MessageArguments = {},
        tags: _TagMapping = {},
    ) -> str:
        """Find the message corresponding to the given ID in the catalog and format it according to the given arguments.
        If the message is either not found or empty, a `KeyError` is raised.
        If the message is incorrectly formatted, an `ICUError` is raised.
        
        See `self._format_message` for acceptable types of the arguments argument.
        
        HTML-like tags in the message used are replaced by their counterpart in `tags`, as specified in `restore_tags`
        """
        return self._process_html_message(
            self.get_message(message_id, context=context), arguments, tags
        )

    def _process_simple_message(
        self, message: str, arguments: _MessageArguments = {}
    ) -> str:
        return self._format_message(message, arguments=arguments, html_escape=False)

    def _process_html_message(
        self, message: str, arguments: _MessageArguments = {}, tags: _TagMapping = {}
    ) -> str:
        return self._format_message(
            self._replace_tags(message, tags), arguments=arguments, html_escape=True
        )

    def _replace_tags(self, target_message: str, tags: _TagMapping) -> str:
        """Replace non-nested tag names and attributes of the `target_message` with the corresponding ones in `tags`
        
        `tags` must be a dict that maps each placeholder in `target_message` to its original tag and attrs,
        e.g. a message like `"Click <a0>here</a0>"` expects tags like `{'a0': {'tag': 'a', 'attrs': {'href': 'http://example.com/pages/1'}}}`
        """
        return restore_tags(target_message, tag_mapping=tags)

    def _format_message(
        self, message: str, arguments: _MessageArguments = {}, html_escape: bool = True
    ) -> str:
        """Substitute arguments into ICU-style message.
        You can have variable substitution, plurals, selects and nested messages.
        
        Raises `ICUError` in case of incorrectly formatted message.
        
        The arguments must be a dict
        """
        return MessageFormat(message, self.icu_locale).format(
            list(arguments.keys()),
            [
                Formattable(escape(x) if html_escape and isinstance(x, str) else x)
                for x in arguments.values()
            ],
        )

    def get_message(self, message_id: str, context: Optional[str] = None) -> str:
        """Find the message corresponding to the given ID in the catalog.
        
        If the message is not found, `None` is returned.
        """
        message = find_string(self.catalog, message_id, context=context)
        if message:
            return message
        else:
            raise KeyError(message_id)


_get_translations = lru_cache(maxsize=len(supported_locales))(
    MessageTranslator.for_application_messages
)
"""Return a `MessageTranslator` for the given locale.

Uses lru_cache in order to parse the message catalogs only once per locale.
"""
