from django.test import RequestFactory, SimpleTestCase
from django.http import HttpResponse
from cjworkbench.middleware.i18n import SetCurrentLocaleMiddleware
from django.contrib.auth.models import AnonymousUser, User
from cjworkbench.i18n import default_locale
from django.utils.translation import get_language

COOKIE_NAME = "workbench_locale"

non_default_locale = "el"
unsupported_locale = "jp"


def mock_response(request):
    response = HttpResponse()
    response.request = request
    return response


class SetCurrentLocaleMiddlewareTest(SimpleTestCase):
    """
    Tests that SetCurrentLocaleMiddleware correctly sets request locale in all cases.
    Locale is set in the current request and in django.

    A user will be served the locale with the following order of preference:
        1. Current GET request parameter, if the locale is supported
        2. Cookie, if the locale is supported
        3. Accept-Language HTTP header, if the header is valid and contains a supported locale
        4. Default locale
    """

    def setUp(self):
        self.factory = RequestFactory()

    def _mock_request(
        self, cookie_locale=None, accept_language_header=None, request_locale=None
    ):
        request = self.factory.get(
            "/" if not request_locale else ("/?locale=" + request_locale)
        )
        request.COOKIES[COOKIE_NAME] = cookie_locale
        if accept_language_header:
            request.META["HTTP_ACCEPT_LANGUAGE"] = accept_language_header
        return request

    def _process_request(self, **kwargs):
        return SetCurrentLocaleMiddleware(mock_response)(self._mock_request(**kwargs))

    def _assert_locale_set(self, response, locale):
        self.assertEqual(
            response.request.locale_id,
            locale,
            msg="Request locale is not set correctly",
        )
        self.assertEqual(
            get_language(), locale, msg="Django locale is not set correctly"
        )

    def test_default(self):
        # anonymous #4
        response = self._process_request()
        self._assert_locale_set(response, default_locale)

    def test_header_only_supported(self):
        # anonymous #3, a simple case: only a supported locale is requested
        response = self._process_request(accept_language_header=non_default_locale)
        self._assert_locale_set(response, non_default_locale)

    def test_header_invalid(self):
        # anonymous #3, invalid header
        response = self._process_request(
            accept_language_header="invalid header content"
        )
        self._assert_locale_set(response, default_locale)

    def test_header_nonsupported(self):
        # anonymous #3, only a non-supported locale is requested
        response = self._process_request(accept_language_header=unsupported_locale)
        self._assert_locale_set(response, default_locale)

    def test_header_multiple(self):
        # anonymous #3, multiple locales requested, one of them is supported
        response = self._process_request(
            accept_language_header="%s,%s;q=0.5"
            % (unsupported_locale, non_default_locale)
        )
        self._assert_locale_set(response, non_default_locale)

    def test_cookie_supported(self):
        # anonymous #2, supported locale
        response = self._process_request(
            accept_language_header=default_locale, cookie_locale=non_default_locale
        )
        self._assert_locale_set(response, non_default_locale)

    def test_cookie_unsupported(self):
        # anonymous #2, non-supported locale
        response = self._process_request(
            accept_language_header=non_default_locale, cookie_locale=unsupported_locale
        )
        self._assert_locale_set(response, non_default_locale)

    def test_request_supported(self):
        # anonymous #1, valid locale
        response = self._process_request(
            accept_language_header=default_locale,
            cookie_locale=default_locale,
            request_locale=non_default_locale,
        )
        self._assert_locale_set(response, non_default_locale)

    def test_request_unsupported(self):
        # anonymous #1, invalid locale
        response = self._process_request(request_locale=unsupported_locale)
        self._assert_locale_set(response, default_locale)
