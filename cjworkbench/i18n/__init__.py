from icu import Locale

supported_locales = ["en", "el"]
default_locale = "en"


LANGUAGE_COOKIE_NAME = "workbench_locale"


def set_language_cookie(response, locale_id):
    response.set_cookie(LANGUAGE_COOKIE_NAME, locale_id, max_age=365 * 86400)


def is_supported(locale_id: str) -> bool:
    return locale_id and locale_id in supported_locales


def get_locale_name(locale_id: str) -> str:
    """Returns the name of the locale represented by `locale_id`, in its own language."""
    locale = Locale(locale_id)
    return locale.getDisplayLanguage(locale)
