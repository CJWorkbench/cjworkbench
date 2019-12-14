from icu import Locale

supported_locales = ["en", "el"]
default_locale = "en"


def is_supported(locale_id: str) -> bool:
    return locale_id and locale_id in supported_locales


def get_locale_name(locale_id: str, in_locale_id: str) -> str:
    """Returns the name of the locale represented by `locale_id` in the language represented by `in_locale_id`.
    """
    return Locale(locale_id).getDisplayLanguage(Locale(in_locale_id))
