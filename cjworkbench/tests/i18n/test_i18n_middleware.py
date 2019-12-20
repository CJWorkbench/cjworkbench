from django.test import RequestFactory, SimpleTestCase
from django.http import HttpResponse
from cjworkbench.middleware.i18n import SetCurrentLocaleMiddleware
from django.contrib.auth.models import AnonymousUser, User
from cjworkbench.i18n import default_locale
from django.utils.translation import get_language
from cjworkbench.middleware.i18n import COOKIE_NAME

non_default_locale = "el"
unsupported_locale = "jp"


def mock_response(request):
    response = HttpResponse()
    response.request = request
    return response


def mock_set_locale_response(new_locale_id):
    def mock_response_edited(request):
        request.locale_id = new_locale_id
        return mock_response(request)

    return mock_response_edited


class MockUserProfile:
    def __init__(self, locale_id=None):
        self.locale_id = locale_id


class MockUser:
    def __init__(self, user_profile__locale_id=None):
        self.is_authenticated = True
        self.user_profile = MockUserProfile(user_profile__locale_id)


class SetCurrentLocaleMiddlewareTest(SimpleTestCase):
    """
    Tests that SetCurrentLocaleMiddleware correctly sets locale in all cases.
    Locale is set in the current request, in cookie, and in django.
            
    A registered user with a locale preference will be served a locale with the following order of preference:
        1. Current GET request parameter, if the locale is supported
        2. User preference, if the locale is supported
        3. Accept-Language HTTP header, if the header is valid and contains a supported locale
        4. Default locale
    The selected locale will not modify the user's preferences, but will set the cookie
    In case any locale is already stored in cookie, it will be ignored
    
    A non-registered user will be served the locale with the following order of preference:
        1. Current GET request parameter, if the locale is supported
        2. Cookie, if the locale is supported
        3. Accept-Language HTTP header, if the header is valid and contains a supported locale
        4. Default locale
    """

    def setUp(self):
        self.factory = RequestFactory()

    def _mock_request(
        self,
        user=None,
        cookie_locale=None,
        accept_language_header=None,
        request_locale=None,
    ):
        request = self.factory.get(
            "/" if not request_locale else ("/?locale=" + request_locale)
        )
        request.COOKIES[COOKIE_NAME] = cookie_locale
        request.user = user or AnonymousUser()
        if accept_language_header:
            request.META["HTTP_ACCEPT_LANGUAGE"] = accept_language_header
        return request

    def _process_request(self, **kwargs):
        return SetCurrentLocaleMiddleware(mock_response)(self._mock_request(**kwargs))

    def _assert_anonymous(self, response, locale):
        self.assertEqual(
            response.request.locale_id,
            locale,
            msg="Request locale is not set correctly",
        )
        self.assertEqual(
            get_language(), locale, msg="Django locale is not set correctly"
        )
        self.assertTrue(
            response.cookies.get(COOKIE_NAME), msg="Cookie locale is not set"
        )
        self.assertEqual(
            response.cookies.get(COOKIE_NAME).value,
            locale,
            msg="Cookie locale is not set correctly",
        )

    def _assert_registered(self, response, locale, *, old_preference):
        self.assertEqual(
            response.request.locale_id,
            locale,
            msg="Request locale is not set correctly",
        )
        self.assertEqual(
            get_language(), locale, msg="Django locale is not set correctly"
        )
        self.assertTrue(
            response.cookies.get(COOKIE_NAME), msg="Cookie locale is not set"
        )
        self.assertEqual(
            response.cookies.get(COOKIE_NAME).value,
            locale,
            msg="Cookie locale is not set correctly",
        )
        self.assertEqual(
            response.request.user.user_profile.locale_id,
            old_preference,
            msg="User settings have been modified",
        )

    def test_anonymous_user_default(self):
        # anonymous #4
        response = self._process_request()
        self._assert_anonymous(response, default_locale)

    def test_anonymous_user_header_only_supported(self):
        # anonymous #3, a simple case: only a supported locale is requested
        response = self._process_request(accept_language_header=non_default_locale)
        self._assert_anonymous(response, non_default_locale)

    def test_anonymous_user_header_invalid(self):
        # anonymous #3, invalid header
        response = self._process_request(
            accept_language_header="invalid header content"
        )
        self._assert_anonymous(response, default_locale)

    def test_anonymous_user_header_nonsupported(self):
        # anonymous #3, only a non-supported locale is requested
        response = self._process_request(accept_language_header=unsupported_locale)
        self._assert_anonymous(response, default_locale)

    def test_anonymous_user_header_multiple(self):
        # anonymous #3, multiple locales requested, one of them is supported
        response = self._process_request(
            accept_language_header="%s,%s;q=0.5"
            % (unsupported_locale, non_default_locale)
        )
        self._assert_anonymous(response, non_default_locale)

    def test_anonymous_user_cookie_supported(self):
        # anonymous #2, supported locale
        response = self._process_request(
            accept_language_header=default_locale, cookie_locale=non_default_locale
        )
        self._assert_anonymous(response, non_default_locale)

    def test_anonymous_user_cookie_unsupported(self):
        # anonymous #2, non-supported locale
        response = self._process_request(
            accept_language_header=non_default_locale, cookie_locale=unsupported_locale
        )
        self._assert_anonymous(response, non_default_locale)

    def test_anonymous_user_request_supported(self):
        # anonymous #1, valid locale
        response = self._process_request(
            accept_language_header=default_locale,
            cookie_locale=default_locale,
            request_locale=non_default_locale,
        )
        self._assert_anonymous(response, non_default_locale)

    def test_anonymous_user_request_unsupported(self):
        # anonymous #1, invalid locale
        response = self._process_request(request_locale=unsupported_locale)
        self._assert_anonymous(response, default_locale)

    def test_registered_user_default(self):
        # registered #4
        response = self._process_request(
            user=MockUser(user_profile__locale_id=unsupported_locale)
        )
        self._assert_registered(
            response, default_locale, old_preference=unsupported_locale
        )

    def test_registered_user_no_session(self):
        # registered, session is ignored
        response = self._process_request(
            user=MockUser(user_profile__locale_id=unsupported_locale),
            cookie_locale=non_default_locale,
        )
        self._assert_registered(
            response, default_locale, old_preference=unsupported_locale
        )

    def test_registered_user_header_supported(self):
        # registered #3, supported locale
        response = self._process_request(
            user=MockUser(user_profile__locale_id=unsupported_locale),
            accept_language_header=non_default_locale,
        )
        self._assert_registered(
            response, non_default_locale, old_preference=unsupported_locale
        )

    def test_registered_user_header_nonsupported(self):
        # registered #3, non-supported locale
        response = self._process_request(
            user=MockUser(user_profile__locale_id=unsupported_locale),
            accept_language_header=unsupported_locale,
        )
        self._assert_registered(
            response, default_locale, old_preference=unsupported_locale
        )

    def test_registered_user_preferences(self):
        # registered #2
        response = self._process_request(
            user=MockUser(user_profile__locale_id=non_default_locale),
            accept_language_header=default_locale,
        )
        self._assert_registered(
            response, non_default_locale, old_preference=non_default_locale
        )

    def test_registered_user_request_supported(self):
        # registered #1, supported locale
        response = self._process_request(
            user=MockUser(user_profile__locale_id=non_default_locale),
            request_locale=default_locale,
        )
        self._assert_registered(
            response, default_locale, old_preference=non_default_locale
        )

    def test_registered_user_request_unsupported(self):
        # registered #1, non-supported locale
        response = self._process_request(
            user=MockUser(user_profile__locale_id=non_default_locale),
            request_locale=unsupported_locale,
        )
        self._assert_registered(
            response, non_default_locale, old_preference=non_default_locale
        )

    def test_locale_changed_by_view(self):
        # Sometimes (i.e., when the locale-changed view has been called),
        # the view changes `request.locale_id`.
        # In that case, we want the final request and cookie to respect the change.
        response = SetCurrentLocaleMiddleware(
            mock_set_locale_response(non_default_locale)
        )(
            self._mock_request(
                accept_language_header=default_locale,
                cookie_locale=default_locale,
                request_locale=default_locale,
            )
        )
        self.assertEqual(
            response.request.locale_id,
            non_default_locale,
            msg="Request locale is not set correctly",
        )
        self.assertTrue(
            response.cookies.get(COOKIE_NAME), msg="Cookie locale is not set"
        )
        self.assertEqual(
            response.cookies.get(COOKIE_NAME).value,
            non_default_locale,
            msg="Cookie locale is not set correctly",
        )
