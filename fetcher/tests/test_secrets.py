import asyncio
import logging
from typing import ContextManager
import unittest
from unittest.mock import patch
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from yarl import URL
from cjwstate import oauth
from cjwstate.models.param_spec import ParamSpec
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
    refresh_url="AIOHTTP_ORIGIN/refresh",
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
                    "id": "TODO_i18n",
                    "arguments": {"text": "Service 'twitter' is no longer configured"},
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


class PrepareSecretOauth2(AioHTTPTestCase):
    GoogleLogic = ParamSpec.Secret.Logic.Oauth2("oauth2", "google")
    IntercomLogic = ParamSpec.Secret.Logic.Oauth2("oauth2", "intercom")

    def setUp(self):
        super().setUp()

        # Tests will set `self.auth_response` to dictate what the server answers.
        self.auth_response = web.Response(status=500, reason="unimplemented")
        self.last_request = None

        self.logger = logging.getLogger("aiohttp.access")
        self.old_log_level = self.logger.level
        self.logger.setLevel(logging.WARN)

        # Hack because request_url changes every test. (Is there a more
        # readable way to make FakeGoogle.refresh_url change each test?)
        self.server.make_url = lambda path: self.server._root.join(
            URL(path.replace("AIOHTTP_ORIGIN", ""))
        )

    def tearDown(self):
        self.logger.setLevel(self.old_log_level)
        super().tearDown()

    async def get_application(self):  # AioHTTPTestCase requirement
        app = web.Application()

        async def handle(request):
            self.last_request = request
            self.last_request_post = await request.post()
            return self.auth_response

        app.router.add_post("/refresh", handle)
        return app

    @unittest_run_loop
    async def test_not_logged_in_gives_none(self):
        self.assertEqual(await prepare_secret(self.GoogleLogic, None), None)

    def fake_google(self) -> ContextManager[None]:
        return patch.object(
            oauth.OAuthService,
            "lookup_or_none",
            lambda s: FakeGoogle(str(self.server._root)),
        )

    @patch.object(oauth.OAuthService, "lookup_or_none", lambda s: None)
    @unittest_run_loop
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
                    "id": "TODO_i18n",
                    "arguments": {"text": "Service 'google' is no longer configured"},
                },
            },
        )

    @patch.object(oauth.OAuthService, "lookup_or_none", lambda s: FakeIntercom)
    @unittest_run_loop
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

    @unittest_run_loop
    async def test_refresh_token_happy_path(self):
        # Google gives access_tokens that only work for a little while. The
        # secret we store in the database has a "refresh_token" to make more.
        self.auth_response = web.json_response(
            {"token_type": "Bearer", "access_token": "an-access-token"}
        )
        with self.fake_google():
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
            self.last_request_post,
            {
                "grant_type": "refresh_token",
                "refresh_token": "a-refresh-token",
                "client_id": "a-client-id",
                "client_secret": "a-client-secret",
            },
        )

    @unittest_run_loop
    async def test_refresh_token_unexpected_http_response(self):
        # Google gives access_tokens that only work for a little while. The
        # secret we store in the database has a "refresh_token" to make more.
        self.auth_response = web.json_response(
            "tea time?", status=418, reason="I'm a teapot"
        )
        with self.fake_google():
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
                        "id": "TODO_i18n",
                        "arguments": {
                            "text": "google responded with HTTP 418 I'm a teapot: 'tea time?'"
                        },
                    },
                },
            )
