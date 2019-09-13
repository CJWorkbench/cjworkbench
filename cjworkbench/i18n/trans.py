from icu import Formattable, ICUError, Locale, MessageFormat, UnicodeString
from babel.messages.pofile import read_po
from bs4 import BeautifulSoup
from django.utils.html import escape

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


def trans(locale, message_id, default=None, context=None, parameters={}):
    """Translates the given message ID to the given locale.
    """
    return _get_translations(locale).trans(message_id, default, context, parameters)

def replace_tags(message):
    """Replaces the HTML tags of a message with placeholders and deletes their attributes.
    
    Placeholders are created as follows: for each tag, the tag is replaced with its name concatenated with the times that a tag with the same name was parsed before,
    i.e. the first <a> tag will be renamed to <a0>, the first <b> tag with <b0>, etc
    Thus, `"Go <b>now></b> to <a href="/index">index</a>"` will be turned to `"Go <b0>now</b0> to <a0>index</a0>"`
    
    Returns a dict with two elements:
      `message`: the new message
      `mapping`: a dict that for each tag placeholder contains its original name `name` and attributes `attrs`
    """
    tag_mapping = {}
    count_tags = {}
    soup = BeautifulSoup(message, 'html.parser')
    for tag in soup.findAll(True):
        count_tags[tag.name] = count_tags.get(tag.name, -1) + 1
        new_name = tag.name + str(count_tags[tag.name])
        tag_mapping[new_name] = {'name': tag.name, 'attrs': tag.attrs}
        tag.name = new_name
        tag.attrs = {}
    
    return {'message': str(soup), 'mapping': tag_mapping}

def restore_tags(message, tag_mapping):
    """Replaces the HTML tags and attributes in a message.
    
    `tag_mapping` is a dict that for each tag name contains a new name `name` and new attributes `attrs`
    
    For each HTML tag found, searches `tag_mapping` for a replacement for its name and attributes.
    If found, replaces with the ones found.
    If not found, removes the tag but keeps the contents.
    
    Returns the new message
    """
    soup = BeautifulSoup(message, 'html.parser')
    for tag in soup.findAll(True):
        if tag.name in tag_mapping:
            tag.attrs = tag_mapping[tag.name].get('attrs', {})
            tag.name = tag_mapping[tag.name]['name']
        else:
            tag.unwrap()
    return str(soup)

class MessageTranslator:
    """Loads the message catalogs for a given locale and provides helper methods for message translation.
    It uses the ICU message format for messages.
    
    Essentially, it is a wrapper for the combination of 
    Babel (for loading PO files) and ICU (for formatting plurals etc) and our HTML placeholder construct.
    """

    def __init__(self, locale):
        try:
            self.locale = Locale.createFromName(locale)
        except Exception as error:
            raise UnsupportedLocaleError(
                "The given locale (%s) is not supported" % locale
            ) from error

        try:
            self.catalog = read_po(open("assets/locale/%s/messages.po" % locale))
        except ValueError as error:
            raise BadCatalogsError(
                "The catalog for the given locale (%s) is badly formatted" % locale
            ) from error
        except Exception as error:
            raise UnsupportedLocaleError(
                "Can't load a catalog for the given locale (%s)" % locale
            ) from error

    def trans(self, message_id, default=None, context=None, parameters={}):
        """Finds the ICU message corresponding to the given ID in the catalog and formats it according to the given parameters.
        If the message is either not found or empty and a non-empty `default` is provided, the `default` is used instead.
        Otherwise, the `message_id` is used instead.
        
        See `self.format_message` for acceptable types of the parameters argument.
        
        In case a message from the catalogs is used, 
            i) HTML-like tags in the message are replaced by their original counterparts in the `default` (or in `message_id`, if `default` is not provided)
            ii) escapes the HTML-like tags not having counterparts in the original (`default` or `message_id`)
        """
        plain = default or message_id
        message = self.get_message(message_id, context=context)
        if message:
            return self.format_message(self.replace_tags(message, plain), parameters=parameters)
        else:
            return self.format_message(plain, parameters=parameters)
        
    def replace_tags(self, target_message, source_message):
        """Replaces tag names and attributes of the `target_message` with the corresponding ones of `source_message`
        
        For deciding correspondence, the tags of the source message are converted to placeholders, as mentioned in `restore_tags` function of this file.
        These placeholders are then searched and replaced in the target_message.
        Any tags of the target message that do not correspond to the source message are deleted (their contents remain).
        """
        return restore_tags(target_message, tag_mapping=replace_tags(source_message)['mapping'])

    def format_message(self, message, parameters={}):
        """Formats the given ICU message according to the given parameters.
        
        When the message needs only one parameter, you can specify it as a scalar value.
        When the message has parameters that look like array indexes, you can specify the parameters with an array.
        In any case, you can specify the parameters as a dict, with (string) keys being the parameter names.
        """
        if not message:
            return message
        message_format = MessageFormat(UnicodeString(message), self.locale)
        try:
            if isinstance(parameters, dict):
                return message_format.format(
                    [UnicodeString(x) for x in parameters.keys()],
                    [Formattable(x) for x in parameters.values()],
                )
            elif isinstance(parameters, (list, tuple)):
                return message_format.format([Formattable(x) for x in parameters])
            else:
                return message_format.format([Formattable(parameters)])
        except ICUError as error:
            raise InvalidICUParameters(
                "The given parameters are invalid for the given message"
            ) from error

    def get_message(self, message_id, context=None):
        """Finds the ICU message corresponding to the given ID in the catalog.
        
        If the message is not found, `None` is returned.
        """
        message = self.catalog.get(message_id, context)
        return message.string if message else None
