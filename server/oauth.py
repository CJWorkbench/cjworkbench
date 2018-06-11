"""Helpers with OAuth 1.0a and OAuth 2.0 sign-ins.

This lets us get offline access tokens for Twitter and Google Drive. Our
modules use these tokens to download data.

At this module's level of abstraction:

    * A `service_id` references a service in `settings.py`
    * `generate_redirect_and_state` returns a (url, state) pair.
    * `receive_code` returns a long-term token.
    * `generate_short_term_token` returns a short-term token.
"""

from django.conf import settings
from typing import Union, Optional, Dict, Tuple
from oauthlib.oauth2.rfc6749.errors import OAuth2Error
import jwt
import requests
import requests_oauthlib


OfflineToken = Dict[str, str]
AccessToken = Dict[str, str]


class OAuthService:
    """OAuth abstraction layer.

    Here's how to use the class, with example data

    Step 1 -- start login
    =====================

    This will send the user to a remote URL to fetch us an authentication
    "code". (Later, we'll exchange the "code" for a "refresh token".)

    .. code-block:: python

        service = OAuthService.lookup_or_none('google_analytics')
        url, state = service.generate_redirect_url_and_state()
        request.session['oauth-state'] = state # prevent CSRF
        redirect(url)

    Step 2 -- acquire refresh token
    ===============================

    The user's web browser gave us a 'code' (in request.GET). We can exchange
    this with the OAuth service for a 'refresh token'.

    In our documentation, we call this return value `OfflineToken`. It is
    a serializable dict.

    .. code-block:: python

        expect_state = request.session['oauth-state'] # _our_ CSRF check
        service = OAuthService.lookup_or_none('google_analytics')
        token = service.acquire_refresh_token_or_str_error(request.GET, expect_state)
        if isinstance(token, str): return token
        email = service.extract_email_from_token(token)
        do_something_with(token, email)

    Step 3 -- use service offline
    =============================

    The server now uses the refresh token to send HTTP requests.

    .. code-block:: python

        service = OAuthService.lookup_or_none('google_analytics')
        token = get_token_we_saved_in_step_2()
        response = service.requests(token).get('https://some.api.server/endpoint')
    """

    def generate_redirect_url_and_state(self) -> Tuple[str, str]:
        """Generate a (url, state) pair we expect will lead to a request on
        redirect_url.

        A good place to store the state is in the user's session.

        The randomly-generated `state` protects against CSRF and replay attacks.
        It protects the service (which won't run the same request twice), and
        it protects _us_ (since we won't have the same `state` across two
        requests).
        """
        raise NotImplementedError


    def acquire_refresh_token_or_str_error(self, GET: Dict[str, str],
                                           expect_state: str) -> Union[OfflineToken, str]:
        """Request a refresh token from the service.

        Return a str message on error. Caller should present this error to
        the user.
        """
        raise NotImplementedError


    def extract_email_from_token(self, token: OfflineToken) -> str:
        """Extract the user account name from the token.
        
        This is fast: it not require an HTTP request.
        """
        raise NotImplementedError


    def requests_or_str_error(self, token: OfflineToken
                             ) -> Union[requests.Session, str]:
        """Build a requests.Session logged in as the user, or return an error
        if not possible.

        This requires an HTTP request to exchange the token for an
        OfflineToken. Return an str error message if that request fails.
        Obvious failures: network error, or the user revoked the token.
        """
        raise NotImplementedError


    @staticmethod
    def lookup_or_none(service_id: str) -> Optional['OAuthService']:
        """Return an OAuthService (if service is configured) or None.
        """
        if service_id not in settings.PARAMETER_OAUTH_SERVICES: return None

        service_dict = dict(settings.PARAMETER_OAUTH_SERVICES[service_id])
        class_name = service_dict.pop('class')
        klass = _classes[class_name]

        return klass(service_id, **service_dict)


class OAuth2(OAuthService):
    def __init__(self, service_id: str, *, client_id: str, client_secret: str,
                 auth_url: str, token_url: str, refresh_url: str, scope: str,
                 redirect_url: str):
        self.service_id = service_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.auth_url = auth_url
        self.token_url = token_url
        self.refresh_url = refresh_url
        self.redirect_url = redirect_url
        self.scope = scope


    def _session(self, token: OfflineToken=None) -> requests_oauthlib.OAuth2Session:
        return requests_oauthlib.OAuth2Session(
            client_id=self.client_id,
            scope=self.scope,
            redirect_uri=self.redirect_url,
            token=token
        )


    def generate_redirect_url_and_state(self) -> Tuple[str, str]:
        session = self._session()
        url, state = session.authorization_url(
            url=self.auth_url,
            # These may be Google-specific. Both are required to make
            # Google return a refresh_token (which we need). If approval_prompt
            # isn't set, Google will return a refresh_token on _first_ request
            # but no refresh_token on _subsequent_ requests.
            access_type='offline', approval_prompt='force'
        )
        return (url, state)


    def acquire_refresh_token_or_str_error(self, GET: Dict[str, str],
                                           expect_state: str) -> Union[OfflineToken, str]:
        if 'code' not in GET:
            return 'Expected auth request to include a "code" parameter.'

        if 'state' not in GET:
            return 'Expected auth request to include a "state" parameter.'

        session = self._session()
        try:
            token = session.fetch_token(
                client_secret=self.client_secret,
                token_url=self.token_url,
                code=GET['code'],
                timeout=30
            )
        except OAuth2Error as err:
            return str(err)

        if not token.get('refresh_token'):
            return f'{self.service_id} returned a token without refresh_token'

        if not token.get('id_token'):
            # Is this Google-specific? OpenID-specific? If so, we may need
            # some other implementation of extract_email_from_token() when we
            # expand to more services.
            return f'{self.service_id} returned a token without JWT id_token'

        return token


    def extract_email_from_token(self, token: OfflineToken) -> str:
        data = jwt.decode(token['id_token'], verify=False)
        return data['email']


    def generate_access_token_or_str_error(self, token: OfflineToken
                                          ) -> Tuple[AccessToken, str]:
        """(OAuth2-only) Generate a temporary access token for the client.

        The client can use the token to make API requests. It will expire after
        a service-defined delay (usually 1hr).
        """
        permanent_session = self._session(token=token)
        access_token = permanent_session.refresh_token(
            self.refresh_url,
            client_id=self.client_id,
            client_secret=self.client_secret
        ) # TODO handle errors: HTTP error, access-revoked error
        return access_token


    def requests_or_str_error(self, token: OfflineToken
                             ) -> Union[requests.Session, str]:
        access_token = self.generate_access_token_or_str_error()
        if isinstance(access_token, str): return access_token
        return self._session(token=access_token)


_classes = {
    'OAuth2': OAuth2,
    #'OAuth1a': OAuth1a,
}
