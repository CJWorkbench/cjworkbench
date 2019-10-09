from cjworkbench.i18n import default_locale, supported_locales
from django.utils.translation import activate
from django.utils.translation.trans_real import (
    language_code_re,
    get_supported_language_variant,
    parse_accept_lang_header,
)


class SetCurrentLocaleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        self._set_locale(request, self._decide_locale(request))

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response

    def _decide_locale(self, request):
        """ Search for the locale to use.
        
        We search in the following places, in order
         1. In the current request attributes, so that the user can change it any time
         2. In the current session, in case it's there from some previous request
         3. In the current user's settings
         4. In the Accept-Language header sent by the browser
         
         If the locale found is not supported, we fallback to the default
        """
        locale = (
            self._get_locale_from_request_attributes(request)
            or self._get_locale_from_session(request)
            or self._get_locale_from_current_user(request)
            or self._get_locale_from_language_header(request)
        )

        return locale if locale in supported_locales else default_locale

    def _get_locale_from_request_attributes(self, request):
        return request.GET.get("locale")

    def _get_locale_from_session(self, request):
        return request.session.get("locale_id")

    def _get_locale_from_current_user(self, request):
        return getattr(request.user, "locale_id", None)

    def _get_locale_from_language_header(self, request):
        # Copied from django.utils.translation.real_trans.get_language_from_request
        accept = request.META.get("HTTP_ACCEPT_LANGUAGE", "")
        for accept_lang, unused in parse_accept_lang_header(accept):
            if accept_lang == "*":
                break

            if not language_code_re.search(accept_lang):
                continue

            try:
                return get_supported_language_variant(accept_lang)
            except LookupError:
                continue
        return None

    def _set_locale(self, request, locale):
        request.locale_id = locale
        # We set the locale of django, in order to
        # a) activate the automatic translation of its translatable elements
        #    (e.g. placeholders of password form inputs)
        # b) have a global source of the current locale
        #    (e.g. for use in lazy translations)
        activate(locale)

        # We set the locale in session, so that we will remember it in future requests
        if request.session.get("locale_id") != locale:
            request.session["locale_id"] = locale
