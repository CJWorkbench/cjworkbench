import asyncio
import json
import logging
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import ContextManager, List, NamedTuple, Tuple
from unittest.mock import patch

from cjwstate import oauth
from cjwstate.modules.param_spec import ParamSpec
from fetcher.secrets import prepare_secret


FakeTwitter = oauth.OAuth1a(
    "twitter",
    consumer_key="a-consumer-key",
    consumer_secret="a-consumer-secret",
    auth_url="notused",
    request_token_url="notused",
    access_token_url="notused",
    redirect_url="notused",
)
FakeIntercom = oauth.OAuth2(
    "intercom",
    client_id="a-client-id",
    client_secret="a-client-secret",
    auth_url="unused",
    token_url="unused",
    refresh_url="HTTP_ORIGIN/refresh",
    scope="unused",
    redirect_url="unused",
)


def FakeGoogle(base_url: str):
    return oauth.OAuth2(
        "google",
        client_id="a-client-id",
        client_secret="a-client-secret",
        auth_url="unused",
        token_url="unused",
        refresh_url=base_url + "/refresh",
        scope="unused",
        redirect_url="unused",
    )


class MockHttpResponse(NamedTuple):
    status_code: int = 200
    """HTTP status code"""

    headers: List[Tuple[str, str]] = []
    """List of headers -- including Content-Length, Transfer-Encoding, etc."""

    body: bytes = b""
    """HTTP response body."""


class PrepareSecretStringTests(unittest.TestCase):
    def test_not_logged_in_gives_none(self):
        self.assertEqual(
            asyncio.run(
                prepare_secret(
                    ParamSpec.Secret.Logic.String(
                        "provider",
                        "label",
                        "pattern",
                        "placeholder",
                        "help",
                        "help_url_prompt",
                        "help_url",
                    ),
                    None,
                )
            ),
            None,
        )

    def test_happy_path(self):
        self.assertEqual(
            asyncio.run(
                prepare_secret(
                    ParamSpec.Secret.Logic.String(
                        "provider",
                        "label",
                        "pattern",
                        "placeholder",
                        "help",
                        "help_url_prompt",
                        "help_url",
                    ),
                    "here-is-my-secret",
                )
            ),
            "here-is-my-secret",
        )


class PrepareSecretOauth1aTests(unittest.TestCase):
    def test_not_logged_in_gives_none(self):
        self.assertEqual(
            asyncio.run(
                prepare_secret(
                    ParamSpec.Secret.Logic.Oauth1a("oauth1a", "twitter"), None
                )
            ),
            None,
        )

    @patch.object(oauth.OAuthService, "lookup_or_none", lambda s: None)
    def test_no_service_gives_error(self):
        self.assertEqual(
            asyncio.run(
                prepare_secret(
                    ParamSpec.Secret.Logic.Oauth1a("oauth1a", "twitter"),
                    {
                        "name": "@testy",
                        "secret": {
                            "user_id": "1234",
                            "oauth_token": "123-abc",
                            "screen_name": "testy",
                            "oauth_token_secret": "123-abc-secret",
                        },
                    },
                )
            ),
            {
                "name": "@testy",
                "error": {
                    "id": "py.fetcher.secrets._service_no_longer_configured_error",
                    "arguments": {"service": "twitter"},
                    "source": None,
                },
            },
        )

    @patch.object(oauth.OAuthService, "lookup_or_none", lambda s: FakeTwitter)
    def test_happy_path(self):
        self.assertEqual(
            asyncio.run(
                prepare_secret(
                    ParamSpec.Secret.Logic.Oauth1a("oauth1a", "twitter"),
                    {
                        "name": "@testy",
                        "secret": {
                            "user_id": "1234",
                            "oauth_token": "123-abc",
                            "screen_name": "testy",
                            "oauth_token_secret": "123-abc-secret",
                        },
                    },
                )
            ),
            {
                "name": "@testy",
                "secret": {
                    "consumer_key": "a-consumer-key",
                    "consumer_secret": "a-consumer-secret",
                    "resource_owner_key": "123-abc",
                    "resource_owner_secret": "123-abc-secret",
                },
            },
        )


class PrepareSecretOauth2(unittest.IsolatedAsyncioTestCase):
    GoogleLogic = ParamSpec.Secret.Logic.Oauth2("oauth2", "google")
    IntercomLogic = ParamSpec.Secret.Logic.Oauth2("oauth2", "intercom")

    def setUp(self):
        super().setUp()

        # Tests will set `self.mock_http_response` to dictate what the server answers.
        self.mock_http_response = None
        self.last_request = None

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self2):
                self.last_request = (self2.command, self2.path, self2.rfile.read1())
                r = self.mock_http_response
                if hasattr(r, "__next__"):
                    r = next(r)
                if r is None:
                    raise RuntimeError("Tests must overwrite self.mock_http_response")

                self2.send_response_only(r.status_code)
                for header, value in r.headers:
                    self2.send_header(header, value)
                self2.end_headers()
                write = self2.wfile.write
                if isinstance(r.body, list):
                    # chunked encoding
                    for chunk in r.body:
                        write(("%x\r\n" % len(chunk)).encode("ascii"))
                        write(chunk)
                        write(b"\r\n")
                    write(b"0\r\n\r\n")
                else:
                    # just write the bytes
                    write(r.body)

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.server_root = "http://" + ":".join(
            str(part) for part in self.server.server_address
        )
        self.server_thread = threading.Thread(
            target=self.server.serve_forever, kwargs={"poll_interval": 0.005}
        )
        self.server_thread.setDaemon(True)
        self.server_thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server_thread.join()

        super().tearDown()

    async def test_not_logged_in_gives_none(self):
        self.assertEqual(await prepare_secret(self.GoogleLogic, None), None)

    def fake_google(self) -> ContextManager[None]:
        return patch.object(
            oauth.OAuthService,
            "lookup_or_none",
            lambda s: FakeGoogle(str(self.server_root)),
        )

    @patch.object(oauth.OAuthService, "lookup_or_none", lambda s: None)
    async def test_no_service_gives_error(self):
        self.assertEqual(
            await prepare_secret(
                self.GoogleLogic,
                {
                    "name": "a@example.com",
                    "secret": {
                        "token_type": "Bearer",
                        "access_token": "do-not-use",
                        "refresh_token": "a-refresh-token",
                    },
                },
            ),
            {
                "name": "a@example.com",
                "error": {
                    "id": "py.fetcher.secrets._service_no_longer_configured_error",
                    "arguments": {"service": "google"},
                    "source": None,
                },
            },
        )

    @patch.object(oauth.OAuthService, "lookup_or_none", lambda s: FakeIntercom)
    async def test_return_access_token_when_no_refresh_token(self):
        # Intercom gives tokens that last forever and doesn't have a refresh_url
        self.assertEqual(
            await prepare_secret(
                self.IntercomLogic,
                {
                    "name": "(unknown)",
                    "secret": {
                        "token_type": "Bearer",
                        "access_token": "intercom-uses-this-one",
                    },
                },
            ),
            {
                "name": "(unknown)",
                "secret": {
                    "token_type": "Bearer",
                    "access_token": "intercom-uses-this-one",
                },
            },
        )

    async def test_refresh_token_happy_path(self):
        # Google gives access_tokens that only work for a little while. The
        # secret we store in the database has a "refresh_token" to make more.
        self.mock_http_response = MockHttpResponse(
            200,
            [("Content-Type", "application/json")],
            b'{"token_type":"Bearer","access_token":"an-access-token"}',
        )
        with self.fake_google():
            with self.assertLogs("httpx._client", level="DEBUG"):
                self.assertEqual(
                    await prepare_secret(
                        self.GoogleLogic,
                        {
                            "name": "a@example.com",
                            "secret": {
                                "token_type": "Bearer",
                                "access_token": "worthless",
                                "refresh_token": "a-refresh-token",
                            },
                        },
                    ),
                    {
                        "name": "a@example.com",
                        "secret": {
                            "token_type": "Bearer",
                            "access_token": "an-access-token",
                        },
                    },
                )
        self.assertEqual(
            self.last_request,
            (
                "POST",
                "/refresh",
                b"grant_type=refresh_token&refresh_token=a-refresh-token&client_id=a-client-id&client_secret=a-client-secret",
            ),
        )

    async def test_refresh_token_unexpected_non_json_response(self):
        self.maxDiff = 99999
        self.mock_http_response = MockHttpResponse(
            200, [("Content-Type", "text/plain; charset=utf-8")], b"tea time?"
        )
        with self.fake_google():
            with self.assertLogs("httpx._client", level="DEBUG"):
                self.assertEqual(
                    await prepare_secret(
                        self.GoogleLogic,
                        {
                            "name": "a@example.com",
                            "secret": {
                                "token_type": "Bearer",
                                "access_token": "worthless",
                                "refresh_token": "a-refresh-token",
                            },
                        },
                    ),
                    {
                        "name": "a@example.com",
                        "error": {
                            "id": "py.fetcher.secrets._refresh_oauth2_token.server_error.general",
                            "arguments": {
                                "service_id": "google",
                                "status_code": 200,
                                "reason": "OK",
                                "description": "tea time?",
                            },
                            "source": None,
                        },
                    },
                )

    async def test_refresh_token_unexpected_status_code(self):
        self.maxDiff = 99999
        self.mock_http_response = MockHttpResponse(
            418,
            [("Content-Type", "application/json")],
            b'{"description":"Bearer","access_token":"an-access-token"}',
        )
        with self.fake_google():
            with self.assertLogs("httpx._client", level="DEBUG"):
                self.assertEqual(
                    await prepare_secret(
                        self.GoogleLogic,
                        {
                            "name": "a@example.com",
                            "secret": {
                                "token_type": "Bearer",
                                "access_token": "worthless",
                                "refresh_token": "a-refresh-token",
                            },
                        },
                    ),
                    {
                        "name": "a@example.com",
                        "error": {
                            "id": "py.fetcher.secrets._refresh_oauth2_token.server_error.general",
                            "arguments": {
                                "service_id": "google",
                                "status_code": 418,
                                "reason": "",
                                "description": '{"description":"Bearer","access_token":"an-access-token"}',
                            },
                            "source": None,
                        },
                    },
                )
