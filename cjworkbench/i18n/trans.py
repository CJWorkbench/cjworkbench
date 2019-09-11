from icu import Formattable, ICUError, Locale, MessageFormat, UnicodeString
from babel.messages.pofile import read_po


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
    """Translates the given message_id to the given locale.
    """
    return _get_translations(locale)._(message_id, default, context, parameters)


class MessageTranslator:
    """Loads the message catalogs for a given locale and provides helper methods for message translation.
    It uses the ICU message format for messages.
    
    Essentially, it is a wrapper for the combination of 
    Babel (for loading PO files) and ICU (for formatting plurals etc).
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
                "The given locale (%s) is not supported" % locale
            ) from error

    def _(self, message_id, default=None, context=None, parameters={}):
        """Finds the ICU message corresponding to the given ID in the catalog and formats it according to the given parameters.
        If the message is not found or is empty and a non-empty default is provided, the default is used instead.
        Otherwise, the message_id is used instead.
        
        See self.format_message for acceptable types of the parameters argument.
        
        """
        return self.format_message(
            self.get_message(message_id, context=context) or (default or message_id),
            parameters=parameters,
        )

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
        
        If the message is not found, None is returned.
        """
        message = self.catalog.get(message_id, context)
        return message.string if message else None
