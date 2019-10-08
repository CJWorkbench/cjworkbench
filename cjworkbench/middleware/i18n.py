from cjworkbench.i18n import default_locale, supported_locales
from django.utils.translation import activate


class SetCurrentLocaleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        locale = request.GET.get("locale")

        if locale not in supported_locales:
            locale = default_locale

        request.locale_id = locale
        # We set the locale of django, in order to 
        # a) activate the automatic translation of its translatable elements
        #    (e.g. placeholders of password form inputs)
        # b) have a global source of the current locale
        #    (e.g. for use in lazy translations)
        activate(locale)

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response
