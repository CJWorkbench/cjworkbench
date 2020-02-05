from bs4 import BeautifulSoup
from django.utils.functional import lazy
from django.utils.html import escape
from django.utils.translation import get_language
from cjworkbench.i18n import default_locale, supported_locales
from cjworkbench.i18n.catalogs import catalog_path
from cjworkbench.i18n.catalogs.util import find_string, read_po_catalog
from string import Formatter
from icu import Formattable, Locale, MessageFormat, ICUError
from babel.messages.catalog import Catalog, Message
from babel.messages.pofile import read_po, PoFileError
from typing import Dict, Union, Optional
import logging
from cjwstate.models.module_registry import MODULE_REGISTRY
from cjwstate.modules.types import ModuleZipfile
from weakref import WeakKeyDictionary
import threading
from io import BytesIO
import importlib.resources
import importlib
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
    return MESSAGE_LOCALIZER_REGISTRY.for_application().localize(
        locale_id, message_id, arguments=arguments
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
    return MESSAGE_LOCALIZER_REGISTRY.for_application().localize_html(
        locale_id, message_id, arguments=arguments, tags=tags, context=context
    )


class NotInternationalizedError(Exception):
    pass


class MessageLocalizer:
    def __init__(self, catalogs: Dict[str, Catalog]):
        self.catalogs = catalogs

    def find_message(
        self, locale_id: str, message_id: str, context: Optional[str] = None
    ) -> str:
        """Find the message with the given id in the given locale.
        
        Raise `KeyError` if the locale has no catalog or the catalog has no such message.
        """
        message = find_string(self.catalogs[locale_id], message_id, context=context)
        if message:
            return message
        else:
            raise KeyError(message_id)

    def localize(
        self, locale_id: str, message_id: str, arguments: _MessageArguments = {}
    ) -> str:
        if locale_id != default_locale:
            try:
                message = self.find_message(locale_id, message_id)
                return icu_format_message(locale_id, message, arguments=arguments)
            except ICUError as err:
                logger.exception(
                    "Error in po file for locale %s and message %s: %s",
                    locale_id,
                    message_id,
                    err,
                )
            except KeyError as err:
                pass
        message = self.find_message(default_locale, message_id)
        return icu_format_message(default_locale, message, arguments=arguments)

    def localize_html(
        self,
        locale_id: str,
        message_id: str,
        *,
        context: Optional[str],
        arguments: _MessageArguments,
        tags: _TagMapping,
    ) -> str:
        if locale_id != default_locale:
            try:
                message = self.find_message(locale_id, message_id, context=context)
                return icu_format_html_message(
                    locale_id, message, arguments=arguments, tags=tags
                )
            except ICUError as err:
                logger.exception(
                    "Error in po file for locale %s and message %s: %s",
                    locale_id,
                    message_id,
                    err,
                )
            except KeyError as err:
                pass
        message = self.find_message(default_locale, message_id, context=context)
        return icu_format_html_message(
            default_locale, message, arguments=arguments, tags=tags
        )


class MessageLocalizerRegistry:
    def __init__(self):
        self._module_localizers = WeakKeyDictionary()
        self._module_localizers_lock = threading.Lock()

    def for_module_zipfile(self, module_zipfile: ModuleZipfile) -> MessageLocalizer:
        """Return a `MessageLocalizer` for the given `ModuleZipFile`

        Raise `NotInternationalizedError` if the `ModuleZipFile` has no valid po files
        
        Caches the result for each `ModuleZipFile`.
        """
        # 1. Get without locking.
        try:
            result = self._module_localizers[module_zipfile]
            if isinstance(result, NotInternationalizedError):
                raise result
            else:
                return result
        except KeyError:
            pass  # fall through

        # 2. Lock, and try again. (This prevents a race.)
        with self._module_localizers_lock:
            try:
                result = self._module_localizers[module_zipfile]
                if isinstance(result, NotInternationalizedError):
                    raise result
                else:
                    return result
            except KeyError:
                pass  # we'll fetch it now

            # 3. Update the cache, still holding the lock.
            try:
                localizer = self._create_localizer_for_module_zipfile(module_zipfile)
                self._module_localizers[module_zipfile] = localizer
                return localizer
            except NotInternationalizedError as err:
                self._module_localizers[module_zipfile] = err
                raise err

            # Release the lock. If another caller is waiting for us to release
            # the lock, now it should check self._cache again.

    @lru_cache(1)
    def for_application(self) -> MessageLocalizer:
        """Return a `MessageLocalizer` for the application messages"""
        catalogs = {}
        for locale_id in supported_locales:
            catalogs[locale_id] = read_po_catalog(catalog_path(locale_id))
        return MessageLocalizer(catalogs)

    @lru_cache(1)
    def for_cjwmodule(self) -> MessageLocalizer:
        """Return a `MessageLocalizer` for the messages of `cjwmodule`"""
        catalogs = {}

        for locale_id in supported_locales:
            try:
                with importlib.resources.open_binary(
                    importlib.import_module(f"cjwmodule.locale.{locale_id}"),
                    "messages.po",
                ) as pofile:
                    catalogs[locale_id] = read_po(pofile, abort_invalid=True)
            except (FileNotFoundError, ModuleNotFoundError) as err:
                if locale_id != default_locale:
                    # This will help us support new languages out-of-order
                    # i.e., translate `cjworkbench` before translating `cjwmodule`.
                    logger.exception(
                        "cjwmodule does not support locale %s: %s", locale_id, err
                    )
                    catalogs[locale_id] = Catalog(locale_id)
                else:
                    raise
        return MessageLocalizer(catalogs)

    def _create_localizer_for_module_zipfile(
        cls, module_zipfile: ModuleZipfile
    ) -> MessageLocalizer:
        catalogs = {}
        for locale_id in supported_locales:
            try:
                catalogs[locale_id] = read_po(
                    BytesIO(module_zipfile.read_messages_po_for_locale(locale_id)),
                    abort_invalid=True,
                )
            except PoFileError as err:
                logger.exception(
                    "Invalid po file for module %s in locale %s: %s",
                    module_zipfile.module_id_and_version,
                    locale_id,
                    err,
                )
                pass
            except KeyError as err:
                pass
        if not catalogs:
            raise NotInternationalizedError(module_zipfile.module_id)
        return MessageLocalizer(catalogs)


MESSAGE_LOCALIZER_REGISTRY = MessageLocalizerRegistry()


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


def icu_format_message(
    locale_id: str, message: str, arguments: _MessageArguments = {}
) -> str:
    """Substitute arguments into ICU-style message.
    You can have variable substitution, plurals, selects and nested messages.
    
    Raises `ICUError` in case of incorrectly formatted message.
    
    The arguments must be a dict
    """
    return MessageFormat(message, Locale.createFromName(locale_id)).format(
        list(arguments.keys()), [Formattable(x) for x in arguments.values()]
    )


def icu_format_html_message(
    locale_id: str,
    message: str,
    arguments: _MessageArguments = {},
    tags: _TagMapping = {},
) -> str:
    """Substitute arguments into ICU-style HTML message.
    You can have variable substitution, plurals, selects and nested messages.
    You can also replace HTML tag placeholders.
    
    Raises `ICUError` in case of incorrectly formatted message.
    """
    return MessageFormat(
        restore_tags(message, tags), Locale.createFromName(locale_id)
    ).format(
        list(arguments.keys()),
        [
            Formattable(escape(x) if isinstance(x, str) else x)
            for x in arguments.values()
        ],
    )
