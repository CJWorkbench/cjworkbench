from icu import Locale

supported_locales = ["en", "el"]
default_locale = "en"


def is_supported(locale_id: str) -> bool:
    return locale_id and locale_id in supported_locales


def get_locale_name(locale_id: str) -> str:
    """Returns the name of the locale represented by `locale_id`, in its own language.
    """
    locale = Locale(locale_id)
    return locale.getDisplayLanguage(locale)
