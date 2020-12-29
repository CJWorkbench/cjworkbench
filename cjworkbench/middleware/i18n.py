import asyncio
from typing import Dict, Any, Optional

from django.utils.decorators import sync_and_async_middleware
from django.utils.translation import activate
from django.utils.translation.trans_real import (
    language_code_re,
    get_supported_language_variant,
    parse_accept_lang_header,
)

from cjworkbench.i18n import default_locale, is_supported, LANGUAGE_COOKIE_NAME


def _augment_request(request):
    locale = LocaleDecider(
        cookies=request.COOKIES,
        accept_language_header=request.META.get("HTTP_ACCEPT_LANGUAGE", ""),
        request_locale_override=request.GET.get("locale"),
    ).decide()

    request.locale_id = locale


@sync_and_async_middleware
def SetCurrentLocaleMiddleware(get_response):
    if asyncio.iscoroutinefunction(get_response):

        async def middleware(request):
            _augment_request(request)
            activate(request.locale_id)  # Django sets an asgiref.local.Local
            return await get_response(request)

    else:

        def middleware(request):
            _augment_request(request)
            activate(request.locale_id)
            return get_response(request)

    return middleware


class SetCurrentLocaleAsgiMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        return await self.inner(
            dict(
                scope,
                locale_id=LocaleDecider(
                    cookies=scope["cookies"],
                    accept_language_header=dict(scope["headers"])
                    .get(b"accept-language", b"")
                    .decode("utf8"),
                ).decide(),
            ),
            receive,
            send,
        )


class LocaleDecider:
    def __init__(
        self,
        *,
        cookies: Dict[str, Any] = {},
        accept_language_header: str = "",
        request_locale_override: str = None,
    ):
        self.cookie = cookies.get(LANGUAGE_COOKIE_NAME)
        self.accept_language_header = accept_language_header
        self.request_locale_override = request_locale_override

    def _only_if_supported(self, locale_id: Optional[str]) -> Optional[str]:
        return locale_id if is_supported(locale_id) else None

    def decide(self) -> str:
        """Search for the locale to use.

        We search in the following places, in order
         1. In the current request attributes, so that the user can change it any time.
            This is meant for testing purposes and does not affect the preferences of logged-in users.
         2. In our language cookie.
         3. In the Accept-Language header sent by the browser
         4. The default locale

         If the locale found at some step is not supported, we proceed to the next step
        """
        return (
            self._get_locale_from_request_override()
            or self._get_locale_from_cookie()
            or self._get_locale_from_language_header()
            or default_locale
        )

    def _get_locale_from_request_override(self) -> Optional[str]:
        return self._only_if_supported(self.request_locale_override)

    def _get_locale_from_cookie(self) -> Optional[str]:
        return self._only_if_supported(self.cookie)

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
