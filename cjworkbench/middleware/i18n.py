from cjworkbench.i18n import default_locale, supported_locales


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

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response
