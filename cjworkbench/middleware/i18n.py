from django.conf import settings


class SetCurrentLocaleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        locale = request.GET.get("locale")

        if locale not in (tup[0] for tup in settings.LANGUAGES):
            locale = settings.LANGUAGE_CODE

        request.locale_id = locale

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response
