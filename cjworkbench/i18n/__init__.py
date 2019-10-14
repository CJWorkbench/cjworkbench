from os import path
from django.utils.translation import activate, get_language
from cjworkbench.i18n.catalogs import catalog_path as get_catalog_path, CATALOG_FILENAME

supported_locales = ["en", "el"]
default_locale = "en"


def is_supported(locale):
    return locale and locale in supported_locales


def catalog_path(locale: str) -> str:
    return get_catalog_path(locale, CATALOG_FILENAME)


set_current_locale = activate


get_current_locale = get_language
