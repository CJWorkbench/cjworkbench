from typing import Any, Dict

from django.contrib.auth.models import User

from cjworkbench.i18n import default_locale, supported_locales, get_locale_name


def context_processor(request) -> dict:
    locale_id = request.locale_id
    return {
        "i18n": dict(
            locale_id=locale_id,
            locale_data=_locale_data(locale_id),
            locales_data=[
                _locale_data(supported_locale_id)
                for supported_locale_id in supported_locales
            ],
        )
    }


def _locale_data(locale_id: str) -> Dict[str, str]:
    return dict(id=locale_id, name=get_locale_name(locale_id))
