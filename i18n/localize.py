from icu import Formattable, Locale, MessageFormat, UnicodeString, ResourceBundle

def trans(message, parameters, locale):
    message_format = MessageFormat(UnicodeString(message), Locale.createFromName(locale))
    if isinstance(parameters, dict):
        return message_format.format(
            [UnicodeString(x) for x in list(parameters.keys())], 
            [Formattable(x) for x in list(parameters.values())]
        )
    elif isinstance(parameters, (list, tuple)):
        return message_format.format([Formattable(x) for x in parameters])

def _(message_id, parameters, locale, default):
    message = get_message(message_id, locale)
    if not message:
        return default
    return trans(message, parameters, locale)

def get_message(message_id, locale):
    try:
        bundle = ResourceBundle('workbench', Locale.createFromName(locale))
        return str(bundle.getStringEx(message_id))
    except:
        return ''
    
class MessageLocalizer:
    def __init__(self, locale):
        self.locale = locale
        
    def _(self, message_id, parameters, default):
        return _(message_id, parameters, default, self.locale)
