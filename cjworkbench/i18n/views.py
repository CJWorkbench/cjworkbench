from django.http import HttpResponseRedirect
from cjworkbench.i18n import is_supported
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
    if request.method == "POST":
        locale = request.POST.get("new_locale")
        if is_supported(locale):
            request.session["locale_id"] = locale
    return HttpResponseRedirect(next)
