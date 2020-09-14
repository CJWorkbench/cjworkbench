from django.http import HttpResponseRedirect
from cjworkbench.i18n import is_supported, set_language_cookie
from urllib.parse import unquote
from django.utils.http import is_safe_url
import json


def set_locale(request):
    """
    Redirect to the referrer URL while setting the chosen language in the session.
    The new language needs to be specified in the request body as `new_locale`.

    Since this view changes how the user will see the rest of the site, it must
    only be accessed as a POST request.

    Based on `django.views.i18n.set_language`
    """
    next = request.POST.get("next", "/")
    if not is_safe_url(
        url=next, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        next = "/"
    response = HttpResponseRedirect(next)
    locale = request.POST.get("new_locale")
    if is_supported(locale):
        request.locale_id = locale
        # Save current locale in a cookie.
        set_language_cookie(response, locale)
        if request.user.is_authenticated:
            request.user.user_profile.locale_id = locale
            request.user.user_profile.save(update_fields=["locale_id"])
    return response
