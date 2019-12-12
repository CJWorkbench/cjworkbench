from cjworkbench.i18n import default_locale, supported_locales, get_locale_name


def context_processor(request) -> dict:
    return get_i18n_context(
        locale=getattr(request, "locale_id", None), user=getattr(request, "user", None)
    )


def get_i18n_context(locale=None, user=None) -> dict:
    current_locale_id = locale or getattr(user, "locale_id", default_locale)
    return {
        "i18n": {
            "locale_id": current_locale_id,
            "locale_data": {
                "id": current_locale_id,
                "name": get_locale_name(current_locale_id, current_locale_id),
            },
            "locales_data": [
                {"id": locale_id, "name": get_locale_name(locale_id)}
                for locale_id in supported_locales
            ],
        }
    }
