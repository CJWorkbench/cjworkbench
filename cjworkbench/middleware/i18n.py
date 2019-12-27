from cjworkbench.i18n import default_locale, is_supported, LANGUAGE_COOKIE_NAME
from django.utils.translation import activate
from django.utils.translation.trans_real import (
    language_code_re,
    get_supported_language_variant,
    parse_accept_lang_header,
)
from typing import Dict, Any, Optional


class SetCurrentLocaleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        locale = LocaleDecider(
            user=request.user,
            cookies=request.COOKIES,
            accept_language_header=request.META.get("HTTP_ACCEPT_LANGUAGE", ""),
            request_locale_override=request.GET.get("locale"),
        ).decide()

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


class SetCurrentLocaleAsgiMiddleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, scope):
        async def inner(receive, send):
            # We modify the scope within `inner`,
            # because only then is `scope["user"]` accessible
            scope["locale_id"] = LocaleDecider(
                user=scope["user"],
                cookies=scope["cookies"],
                accept_language_header=dict(scope["headers"])
                .get(b"accept-language", b"")
                .decode("utf8"),
            ).decide()
            return await self.app(scope)(receive, send)

        return inner


class LocaleDecider:
    def __init__(
        self,
        *,
        user,
        cookies: Dict[str, Any] = {},
        accept_language_header: str = "",
        request_locale_override: str = None,
    ):
        self.user = user
        self.cookie = cookies.get(LANGUAGE_COOKIE_NAME)
        self.accept_language_header = accept_language_header
        self.request_locale_override = request_locale_override

    def _only_if_supported(self, locale_id: Optional[str]) -> Optional[str]:
        return locale_id if is_supported(locale_id) else None

    def decide(self) -> str:
        """ Search for the locale to use.
        
        We search in the following places, in order
         1. In the current request attributes, so that the user can change it any time.
            This is meant for testing purposes and does not affect the preferences of logged-in users.
         2. If the user is logged in and has ever set a locale preference, in the user's profile;
            otherwise, in our language cookie.
         3. In the Accept-Language header sent by the browser
         4. The default locale
         
         If the locale found at some step is not supported, we proceed to the next step
        """
        return (
            self._get_locale_from_request_override()
            or self._get_locale_from_current_user()
            or self._get_locale_from_language_header()
            or default_locale
        )

    def _get_locale_from_request_override(self) -> Optional[str]:
        return self._only_if_supported(self.request_locale_override)

    def _get_locale_from_current_user(self) -> Optional[str]:
        if not self.user.is_authenticated:
            return self._only_if_supported(self.cookie)
        else:
            return self._only_if_supported(self.user.user_profile.locale_id)

    def _get_locale_from_language_header(self) -> Optional[str]:
        # Logic adapted from django.utils.translation.real_trans.get_language_from_request
        for accept_lang, unused in parse_accept_lang_header(
            self.accept_language_header
        ):
            if accept_lang == "*":
                break

            if not language_code_re.search(accept_lang):
                continue

            try:
                locale_id = get_supported_language_variant(accept_lang)
            except LookupError:
                continue

            if is_supported(locale_id):
                return locale_id
            else:
                continue
        return None
