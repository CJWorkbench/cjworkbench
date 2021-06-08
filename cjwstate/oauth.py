"""Helpers with OAuth 1.0a and OAuth 2.0 sign-ins.

This lets us get offline access tokens for Twitter and Google Drive. Our
modules use these tokens to download data.

At this module's level of abstraction:

    * A `service_id` references a service in `settings.py`
    * An `OAuthService` deals in tokens, not HTTP requests.
    * OAuth 1 and OAuth 2 behave the same way (though some methods will only
      work with one or the other).
    * A "refresh token" (or "OfflineToken") is a long-term token we must never
      show the user. This is "oauth token" in OAuth 1 and "refresh token" in
      OAuth 2.
    * An "access token" is a short-term token. It's "access token" in OAuth 1
      and there is no such concept in OAuth 2.

Currently we support Twitter (OAuth 1.0a) and Google (OAuth 2). Each provider
has peculiarities, so as we add more we'll need more hacks.

TODO create a lovely HTTP-level test suite.
"""

from django.conf import settings
from typing import Union, Optional, Dict, Tuple
from oauthlib.oauth2.rfc6749.errors import OAuth2Error
import jwt
import requests_oauthlib
from requests_oauthlib.oauth1_session import TokenRequestDenied
import json
from urllib.parse import urlencode

__all__ = ["TokenRequestDenied", "OAuthService", "OAuth1a", "OAuth2"]


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

        service = OAuthService.lookup_or_none('google')
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
        service = OAuthService.lookup_or_none('google')
        token = service.acquire_refresh_token_or_str_error(request.GET, expect_state)
        if isinstance(token, str):
            return token
        do_something_with(token)

    Step 3 -- use service offline
    =============================

    The server now uses the refresh token to send HTTP requests.

    .. code-block:: python

        service = OAuthService.lookup_or_none('google')
        offline_token = get_token_we_saved_in_step_2()
        token = service.generate_access_token_or_str_error(offline_token)
        # Now pass `token` to the user's web browser
    """

    def generate_redirect_url_and_state(self) -> Tuple[str, str]:
        """Generate a (url, state) pair we expect will lead to a request on
        redirect_url.

        A good place to store the state is in the user's session.

        The randomly-generated `state` protects against CSRF and replay attacks.
        It protects the service (which won't run the same request twice), and
        it protects _us_ (since we won't have the same `state` across two
        requests).

        Raises requests_oauthlib.oauth1_session.TokenRequestDenied if we're
        OAuth 1 and the server rejected us.
        """
        raise NotImplementedError

    def acquire_refresh_token_or_str_error(
        self, GET: Dict[str, str], expect_state: str
    ) -> Union[OfflineToken, str]:
        """
        Request a refresh token from the service.

        Return a str message on error. Caller should present this error to
        the user.
        """
        raise NotImplementedError

    @staticmethod
    def lookup_or_none(service_id: str) -> Optional["OAuthService"]:
        """Return an OAuthService (if service is configured) or None."""
        if service_id not in settings.OAUTH_SERVICES:
            return None

        service_dict = dict(settings.OAUTH_SERVICES[service_id])
        class_name = service_dict.pop("class")
        klass = _classes[class_name]

        return klass(service_id, **service_dict)


class OAuth1a(OAuthService):
    def __init__(
        self,
        service_id: str,
        *,
        consumer_key: str,
        consumer_secret: str,
        auth_url: str,
        request_token_url: str,
        access_token_url: str,
        redirect_url: str,
    ):
        self.service_id = service_id
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.auth_url = auth_url
        self.request_token_url = request_token_url
        self.access_token_url = access_token_url
        self.redirect_url = redirect_url

    def _session(self, **kwargs) -> requests_oauthlib.OAuth1Session:
        return requests_oauthlib.OAuth1Session(
            client_key=self.consumer_key,
            client_secret=self.consumer_secret,
            callback_uri=self.redirect_url,
        )

    def generate_redirect_url_and_state(self) -> Tuple[str, str]:
        session = self._session()

        # raises TokenRequestDenied
        request_token = session.fetch_request_token(self.request_token_url)

        url = session.authorization_url(self.auth_url)

        return (url, json.dumps(request_token))

    def acquire_refresh_token_or_str_error(
        self, GET: Dict[str, str], expect_state: str
    ) -> Union[OfflineToken, str]:
        if "oauth_token" not in GET or "oauth_verifier" not in GET:
            return "Missing oauth_token or oauth_verifier in URL"

        try:
            request_token = json.loads(expect_state)
        except json.JSONDecodeError:
            return "Could not parse state"

        session = self._session()
        session.token = request_token
        session.parse_authorization_response("http://foo?" + urlencode(GET))

        try:
            # raises:
            #
            # * requests_oauthlib.oauth1_session.TokenRequestDenied
            #   (child of ValueError) on server error response
            # * ValueError on badly-encoded server response
            # * TokenMissing (child of ValueError) on server response
            #   missing data
            #
            # These are all ValueError
            offline_token = session.fetch_access_token(self.access_token_url)
        except ValueError as err:
            return str(err)

        return offline_token

    def extract_username_from_token(self, token: OfflineToken) -> str:
        return "@" + token["screen_name"]  # Twitter-specific...


class OAuth2(OAuthService):
    def __init__(
        self,
        service_id: str,
        *,
        client_id: str,
        client_secret: str,
        auth_url: str,
        token_url: str,
        refresh_url: str,
        scope: str,
        redirect_url: str,
    ):
        self.service_id = service_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.auth_url = auth_url
        self.token_url = token_url
        self.refresh_url = refresh_url
        self.redirect_url = redirect_url
        self.scope = scope

    def _session(self, token: OfflineToken = None) -> requests_oauthlib.OAuth2Session:
        return requests_oauthlib.OAuth2Session(
            client_id=self.client_id,
            scope=self.scope,
            redirect_uri=self.redirect_url,
            token=token,
        )

    def generate_redirect_url_and_state(self) -> Tuple[str, str]:
        session = self._session()
        url, state = session.authorization_url(
            url=self.auth_url,
            # These may be Google-specific. Both are required to make
            # Google return a refresh_token (which we need). If approval_prompt
            # isn't set, Google will return a refresh_token on _first_ request
            # but no refresh_token on _subsequent_ requests.
            access_type="offline",
            approval_prompt="force",
        )
        return (url, state)

    def acquire_refresh_token_or_str_error(
        self, GET: Dict[str, str], expect_state: str
    ) -> Union[OfflineToken, str]:
        if "code" not in GET:
            return 'Expected auth request to include a "code" parameter.'

        if "state" not in GET:
            return 'Expected auth request to include a "state" parameter.'

        session = self._session()
        try:
            token = session.fetch_token(
                client_secret=self.client_secret,
                token_url=self.token_url,
                code=GET["code"],
                include_client_id=True,  # for Intercom
                timeout=30,
            )
        except OAuth2Error as err:
            return str(err)

        # Google secrets are dicts with {'refresh_token':..., 'id_token': ...}
        # Intercom secrets are dicts with {'access_token': ..., 'token': ...}
        # (and access_token == token).

        return token

    def extract_username_from_token(self, token: OfflineToken) -> str:
        try:
            # Google provides a JWT-encoded id_token
            data = jwt.decode(token["id_token"], options={"verify_signature": False})
            return data["email"]
        except KeyError:
            # Intercom provides no information at all about the user
            return "(connected)"

    def generate_access_token_or_str_error(
        self, token: OfflineToken
    ) -> Tuple[AccessToken, str]:
        """(OAuth2-only) Generate a temporary access token for the client.

        The client can use the token to make API requests. It will expire after
        a service-defined delay (usually 1hr).
        """
        permanent_session = self._session(token=token)
        access_token = permanent_session.refresh_token(
            self.refresh_url, client_id=self.client_id, client_secret=self.client_secret
        )  # TODO handle errors: HTTP error, access-revoked error
        return access_token


_classes = {"OAuth2": OAuth2, "OAuth1a": OAuth1a}
