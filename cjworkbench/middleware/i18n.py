from django.conf import settings


class SetCurrentLocaleMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        locale = None

        if request.user.is_staff:
            locale = request.GET.get("locale")

        if not (locale in map(lambda p: p[0], settings.LANGUAGES)):
            locale = settings.LANGUAGE_CODE

        request.currentLocale = locale

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response
