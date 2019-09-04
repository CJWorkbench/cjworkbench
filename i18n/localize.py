from icu import Formattable, ICUError, Locale, MessageFormat, UnicodeString
from babel.messages.pofile import read_po
    
class UnsupportedLocaleError(Exception):
    '''Indicates that an unsupported locale is (attempted to be) used
    
    A locale may be unsupported because its not recognised as a locale
    or because there are no catalogs for it.
    '''
        
class BadCatalogsError(Exception):
    '''Indicates that the catalog for a locale is not properly formatted
    
    A possible formatting error is empty comments at the start of the file.
    '''
        
class InvalidICUParameters(Exception):
    '''Indicates that the parameters passed for a message are not valid
    
    For example, you may have passed a string in the place of an integer.
    '''
        
class MessageLocalizer:
    '''Loads the message catalogs for a given locale and provides helper methods for message translation.
    It uses the ICU message format for messages.
    
    Essentially, it is a wrapper for the combination of 
    Babel (for loading PO files) and ICU (for formatting plurals etc).
    '''
    def __init__(self, locale):
        try:
            self.locale = Locale.createFromName(locale)
        except Exception as error:
            raise UnsupportedLocaleError('The given locale (%s) is not supported' % locale) from error
            
        try:
            self.catalog = read_po(open('assets/locale/%s/messages.po' % locale))
        except ValueError as error:
            raise BadCatalogsError('The catalog for the given locale (%s) is badly formatted' % locale) from error
        except Exception as error:
            raise UnsupportedLocaleError('The given locale (%s) is not supported' % locale) from error
        
    def _(self, message_id, default=None, parameters={}):
        return self.trans(self.get_message(message_id, default=default), parameters=parameters)
        
    def trans(self, message, parameters={}):
        if not message:
            return message
        message_format = MessageFormat(UnicodeString(message), self.locale)
        try:
            if isinstance(parameters, dict):
                return message_format.format(
                    [UnicodeString(x) for x in parameters.keys()], 
                    [Formattable(x) for x in parameters.values()]
                )
            elif isinstance(parameters, (list, tuple)):
                return message_format.format([Formattable(x) for x in parameters])
        except ICUError as error:
            raise InvalidICUParameters('The given parameters are invalid for the given message') from error
        
    def get_message(self, message_id, default=None):
        message = self.catalog.get(message_id)
        if(message):
            return message.string
        else: 
            return default
