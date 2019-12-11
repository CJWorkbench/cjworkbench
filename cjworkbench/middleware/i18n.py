from cjworkbench.i18n import default_locale, is_supported
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
        locale = self._decide_locale(request)

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

    def _decide_locale(self, request):
        """ Search for the locale to use.
        
        We search in the following places, in order
         1. In the current request attributes, so that the user can change it any time.
            This is meant for testing purposes and does not affect the preferences of logged-in users.
         2. If the user is logged in and has ever set a locale preference, in the user's profile;
            otherwise, in the current session.
         3. In the Accept-Language header sent by the browser
         4. The default locale
         
         If the locale found at some step is not supported, we proceed to the next step
         
         If the user is not logged in or has never set a locale preference, the selected locale is saved in session
        """
        locale = (
            self._get_locale_from_query(request)
            or self._get_locale_from_current_user(request)
            or self._get_locale_from_language_header(request)
        )

        return locale if is_supported(locale) else default_locale

    def _get_locale_from_query(self, request):
        locale = request.GET.get("locale")
        return locale if is_supported(locale) else None

    def _get_locale_from_current_user(self, request):
        if self._use_session(request.user):
            locale = request.session.get("locale_id")
            return locale if is_supported(locale) else None
        else:
            locale = getattr(request.user.user_profile, "locale_id", None)
            return locale if is_supported(locale) else None

    def _use_session(self, user):
        return not user.is_authenticated or not hasattr(user.user_profile, "locale_id")

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
