from babel.messages.pofile import read_po
from bs4 import BeautifulSoup
from django.utils.html import escape
from cjworkbench.i18n import catalog_path


class UnsupportedLocaleError(Exception):
    """Indicates that an unsupported locale is (attempted to be) used
    
    A locale may be unsupported because its not recognised as a locale
    or because there are no catalogs for it.
    """


class BadCatalogsError(Exception):
    """Indicates that the catalog for a locale is not properly formatted
    
    A possible formatting error is empty comments at the start of the file.
    """


class InvalidICUParameters(Exception):
    """Indicates that the parameters passed for a message are not valid
    
    For example, you may have passed a string in the place of an integer.
    """


_translators = {}


def _get_translations(locale):
    """Returns a MessageTranslator object for the given locale.
    
    In order to parse the message catalogs only once per locale,
    uses the _translators dict to store the created MessageTranslator for each locale.
    """
    if locale in _translators:
        return _translators[locale]
    _translators[locale] = MessageTranslator(locale)
    return _translators[locale]


def trans(locale, message_id, default=None, context=None, parameters={}, tags={}):
    """Translates the given message ID to the given locale.
    """
    return _get_translations(locale).trans(
        message_id, default, context, parameters, tags
    )


def restore_tags(message, tag_mapping):
    """Replaces the HTML tags and attributes in a message.
    
    `tag_mapping` is a dict that for each tag name contains a new name `name` and new attributes `attrs`
    
    For each non-nested HTML tag found, searches `tag_mapping` for a replacement for its name and attributes.
    If found, replaces with the ones found.
    If not found, removes the tag but keeps the contents.
    
    Nested HTML tags are escaped
    
    Returns the new message
    """
    soup = BeautifulSoup(message, "html.parser")
    for child in soup.children:
        if child.name:  # i.e. child is a tag
            if child.name in tag_mapping:
                child.attrs = tag_mapping[child.name].get("attrs", {})
                child.name = tag_mapping[child.name]["tag"]
            else:
                child.unwrap()
    return str(soup)


class MessageTranslator:
    """Loads the message catalogs for a given locale and provides helper methods for message translation.
    It uses plaintext messages with variables in `{var}` placeholders, e.g. in `"Hello {name}"`, `name` is a variable.
    
    Essentially, it is a wrapper for the combination of 
    Babel (for loading PO files) and variable substitution and our HTML placeholder construct.
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
        """Finds the message corresponding to the given ID in the catalog and formats it according to the given parameters.
        If the message is either not found or empty and a non-empty `default` is provided, the `default` is used instead.
        Otherwise, the `message_id` is used instead.
        
        See `self.format_message` for acceptable types of the parameters argument.
        
        In case a message from the catalogs is used, 
            i) non-nested HTML-like tags in the message are replaced by their original counterparts in the `tags` parameter;
               if they have no counterparts, they are replaced by their (escaped) contents
            ii) escapes the nested HTML-like tags
        """
        plain = default or message_id
        message = self.get_message(message_id, context=context)
        if message:
            return self.format_message(
                self.replace_tags(message, tags), parameters=parameters
            )
        else:
            return self.format_message(plain, parameters=parameters)

    def replace_tags(self, target_message, tags):
        """Replaces non-nested tag names and attributes of the `target_message` with the corresponding ones in `tags`
        
        `tags` must be a dict that maps each placeholder in `target_message` to its original tag and attrs,
        e.g. a message like `"Click <a0>here</a0>"` expects tags like `{'a0': {'tag': 'a', 'attrs': {'href': 'http://example.com/pages/1'}}}`
        """
        return restore_tags(target_message, tag_mapping=tags)

    def format_message(self, message, parameters={}):
        """Formats the given message according to the given parameters.
        
        When the message has parameters that look like array indexes, you can specify the parameters with a list/tuple.
        When the message needs a list/tuple of one element, you can specify it as a scalar value.
        In other cases, you can specify the parameters as a dict, with keys being the parameter names.
        """
        if not message:
            return message
        try:

            if isinstance(parameters, dict):
                return message.format(**parameters)
            elif isinstance(parameters, (list, tuple)):
                return message.format(parameters)
            else:
                return message.format(parameters)

            return message.format(**parameters)
        except Exception as error:
            raise InvalidICUParameters(
                "The given parameters are invalid for the given message"
            ) from error

    def get_message(self, message_id, context=None):
        """Finds the message corresponding to the given ID in the catalog.
        
        If the message is not found, `None` is returned.
        """
        if context:
            message = self.catalog.get(message_id, context)
        else:
            message = self.catalog.get(message_id)
        return message.string if message else None
