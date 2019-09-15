from os import path

supported_locales = ['en', 'el']
default_locale = 'en'

def catalog_path(locale, catalog="messages.po"):
    return path.join("assets", "locale", locale, catalog)
