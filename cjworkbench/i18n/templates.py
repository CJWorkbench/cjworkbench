from cjworkbench.i18n import default_locale


def context_processor(request) -> dict:
    return get_i18n_context(
        locale=getattr(request, "locale_id", None), user=getattr(request, "user", None)
    )


def get_i18n_context(locale=None, user=None) -> dict:
    return {
        "i18n": {
            "locale_id": locale or getattr(user, "locale_id", default_locale),
            "show_switcher": getattr(user, "is_staff", False) if user else False,
        }
    }
