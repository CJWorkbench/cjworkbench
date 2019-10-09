from os import path
from django.utils.translation import activate, get_language

supported_locales = ["en", "el"]
default_locale = "en"


def is_supported(locale):
    return locale and locale in supported_locales


def catalog_path(locale: str, catalog: str = "messages.po") -> str:
    return path.join("assets", "locale", locale, catalog)


set_current_locale = activate


get_current_locale = get_language
