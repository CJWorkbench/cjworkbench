from babel.messages.pofile import read_po
from bs4 import BeautifulSoup
from django.utils.html import escape
from cjworkbench.i18n import catalog_path
from string import Formatter


class UnsupportedLocaleError(Exception):
    """An unsupported locale is (attempted to be) used
    
    A locale may be unsupported because its not recognised as a locale
    or because there are no catalogs for it.
    """


class BadCatalogsError(Exception):
    """The catalog for a locale is not properly formatted
    
    A possible formatting error is empty comments at the start of the file.
    """


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


def trans(locale, message_id, *, default, context=None, parameters={}, tags={}):
    """Translate the given message ID to the given locale.
    """
    return _get_translations(locale).trans(
        message_id, default, context, parameters, tags
    )


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

        try:
            self.catalog = read_po(open(catalog_path(locale)))
        except ValueError as error:
            raise BadCatalogsError(
                "The catalog for the given locale (%s) is badly formatted" % locale
            ) from error
        except Exception as error:
            raise UnsupportedLocaleError(
                "Can't load a catalog for the given locale (%s)" % locale
            ) from error

    def trans(self, message_id, default=None, context=None, parameters={}, tags={}):
        """Find the message corresponding to the given ID in the catalog and format it according to the given parameters.
        If the message is either not found or empty and a non-empty `default` is provided, the `default` is used instead.
        
        See `self._format_message` for acceptable types of the parameters argument.
        
        In case a message from the catalogs is used, if the message contains illegal (i.e. numeric) variables, 
        they are handled so as to not raise an exception; at this point, the default message is used instead, but you should not rely on this behaviour
        
        HTML-like tags in the message used are replaced by their counterpart in `tags`, as specified in `restore_tags`
        """
        return self._process_message(
            self.get_message(message_id, context=context),
            default or message_id,
            parameters,
            tags,
        )

    def _process_message(self, message, fallback, parameters={}, tags={}):
        if message:
            try:
                return self._format_message(
                    self._replace_tags(message, tags), parameters=parameters
                )
            except Exception:
                pass
        return self._format_message(
            self._replace_tags(fallback, tags), parameters=parameters
        )

    def _replace_tags(self, target_message, tags):
        """Replace non-nested tag names and attributes of the `target_message` with the corresponding ones in `tags`
        
        `tags` must be a dict that maps each placeholder in `target_message` to its original tag and attrs,
        e.g. a message like `"Click <a0>here</a0>"` expects tags like `{'a0': {'tag': 'a', 'attrs': {'href': 'http://example.com/pages/1'}}}`
        """
        return restore_tags(target_message, tag_mapping=tags)

    def _format_message(self, message, parameters={}):
        """Substitute parameters into ICU-style message.
        At this point, ICU is not actually supported (i.e. you can have no plurals, secects, etc).
        Only variable substitution is supported.
        
        The parameters must be a dict
        """
        if not message:
            return message
        if isinstance(parameters, dict):
            try:
                return formatter.format(
                    message,
                    **{
                        key: (
                            escape(parameters[key])
                            if isinstance(parameters[key], str)
                            else parameters[key]
                        )
                        for key in parameters
                    },
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


class PartialFormatter(Formatter):
    def get_field(self, field_name, args, kwargs):
        # Handle a key not found
        try:
            return super().get_field(field_name, args, kwargs)
        except (KeyError, AttributeError):
            return "{%s}" % field_name, field_name


formatter = PartialFormatter()
