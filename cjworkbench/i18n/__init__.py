from os import path

supported_locales = ["en", "el"]
default_locale = "en"


def is_supported(locale):
    return locale and locale in supported_locales
