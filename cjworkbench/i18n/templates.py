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
            "show_switcher": getattr(user, "is_staff", False) if user else False,
            "locales_data": [
                {
                    "locale_id": locale_id,
                    "locale_name": get_locale_name(locale_id, current_locale_id),
                }
                for locale_id in supported_locales
            ],
        }
    }
