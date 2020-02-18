from cjworkbench.i18n import default_locale, supported_locales, get_locale_name


def context_processor(request) -> dict:
    return get_i18n_context(
        locale_id=getattr(request, "locale_id", None),
        user=getattr(request, "user", None),
    )


def get_i18n_context(locale_id=None, user=None) -> dict:
    current_locale_id = locale_id or (
        user.user_profile.locale_id if user else default_locale
    )
    return {
        "i18n": {
            "locale_id": current_locale_id,
            "locale_data": {
                "id": current_locale_id,
                "name": get_locale_name(current_locale_id),
            },
            "locales_data": [
                {
                    "id": supported_locale_id,
                    "name": get_locale_name(supported_locale_id),
                }
                for supported_locale_id in supported_locales
            ],
        }
    }
