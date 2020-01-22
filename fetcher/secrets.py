import asyncio
from functools import singledispatch
from typing import Any, Dict, List, Optional
import aiohttp
from cjwkernel.types import I18nMessage
from cjwstate import oauth
from cjwstate.modules.param_spec import ParamSpec, ParamSpecSecret


UserProvidedSecret = Optional[Dict[str, Any]]
ModuleSecret = Optional[Dict[str, Any]]


async def prepare_secrets(
    fields: List[ParamSpec], values: Dict[str, UserProvidedSecret]
) -> Dict[str, ModuleSecret]:
    """
    Given secrets set by the user, build secrets for a module's `fetch()` call.

    The logic varies by SecretLogic. If you're trying to understand how a
    particular secret's value will appear, read the docs of logic-specific
    functions in this module (e.g., `prepare_secret_oauth2()`).

    With all secret logics, we have two main goals:

        * Hide from the module anything it doesn't need.
        * Abstract and document all errors, so fetch() authors can see them.

    Do not expect errors: this function should recover from all errors and
    return values that make sense to the module.
    """
    return {
        field.id_name: await prepare_secret(
            field.secret_logic, values.get(field.id_name)
        )
        for field in fields
        if isinstance(field, ParamSpecSecret)
    }


def _secret_error(user_secret: Dict[str, Any], message: I18nMessage) -> Dict[str, Any]:
    retval = {**user_secret, "error": message.to_dict()}
    del retval["secret"]
    return retval


@singledispatch
async def prepare_secret(
    logic: ParamSpecSecret.Logic, value: UserProvidedSecret
) -> ModuleSecret:
    """
    Convert the user-provided value in `wf_module.secrets` to module format.

    The logic varies by SecretLogic. If you're trying to understand how a
    particular secret's value will appear, read the docs of logic-specific
    functions in this module (e.g., `prepare_secret_oauth2()`).
    """
    raise NotImplementedError


@prepare_secret.register(ParamSpecSecret.Logic.Oauth1a)
async def prepare_secret_oauth1a(
    logic: ParamSpecSecret.Logic.Oauth1a, value: UserProvidedSecret
) -> ModuleSecret:
    """
    Prepare an OAuth1a secret for a module fetch() call.

    SECURITY: beware: we provide the module with our consumer secret. The
    module can masquerade as Workbench. The module will be able to authenticate
    with the provider as the end user, forever.

    A non-`None` UserProvidedSecret has a "secret" sub-dict with keys:

        * `oauth_token`: OAuth 1.0a access token provided by service for user.
        * `oauth_token_secret`: OAuth 1.0 access token provided by service for user.

    On success, ModuleSecret "secret" sub-dict will have keys:

        * `consumer_key`: for signing requests.
        * `consumer_secret`: for signing requests.
        * `resource_owner_key`: `oauth_token` (OAuth 1.0a access token)
        * `resource_owner_secret`: `oauth_token_secret` (OAuth 1.0a access token)

    Otherwise, ModuleSecret "error" value will be an I18nMessage-compatible
    dict describing the problem.

    All problems that may cause an "error":

        * After the user set a valid secret, Workbench was reconfigured and the
          provider was disabled.
    """
    if not value:
        return None

    service: oauth.OAuth1 = oauth.OAuthService.lookup_or_none(logic.service)
    if not service:
        return _secret_error(
            value,
            I18nMessage.TODO_i18n("Service %r is no longer configured" % logic.service),
        )

    return {
        **value,
        "secret": {
            "consumer_key": service.consumer_key,
            "consumer_secret": service.consumer_secret,
            "resource_owner_key": value.get("secret", {}).get("oauth_token", ""),
            "resource_owner_secret": value.get("secret", {}).get(
                "oauth_token_secret", ""
            ),
        },
    }


class _RefreshOauth2TokenError(Exception):
    def __init__(self, *args):
        super().__init__(*args)
        assert isinstance(args[0], I18nMessage)
        self.i18n_message = args[0]


async def _refresh_oauth2_token(
    service: oauth.OAuth2, refresh_token: str
) -> Dict[str, Any]:
    """
    Exchange a "refresh_token" for an "access_token" and "token_type".

    This involves an HTTP request to an OAuth2 token server.

    Raise _RefreshOauth2TokenError on error.

    ref: https://www.oauth.com/oauth2-servers/access-tokens/refreshing-access-tokens/
    """
    timeout = aiohttp.ClientTimeout(total=60)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                service.refresh_url,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": service.client_id,
                    "client_secret": service.client_secret,
                },
            ) as response:
                # Most of these error cases are _very_ unlikely -- to the point
                # that we should write error messages only after experiencing
                # most in production....

                # raises ClientPayloadError, ClientResponseError (ContentTypeError),
                # asyncio.TimeoutError
                body = await response.json(encoding="utf-8")

                if (response.status // 400) == 1 and "error" in body:
                    # Includes errors that are part of the OAuth2 spec.
                    # TODO we can actually translate some of these error codes. ref:
                    # https://www.oauth.com/oauth2-servers/access-tokens/access-token-response/#error
                    raise _RefreshOauth2TokenError(
                        I18nMessage.TODO_i18n(
                            "Token server responded with %d: %s (%r)"
                            % (
                                response.status,
                                str(body["error"]),
                                body.get("error_description"),
                            )
                        )
                    )
                if response.status != 200:
                    # Probably a server error. Servers don't usually break.
                    raise _RefreshOauth2TokenError(
                        I18nMessage.TODO_i18n(
                            "%s responded with HTTP %d %s: %r"
                            % (
                                service.service_id,
                                response.status,
                                response.reason,
                                body,
                            )
                        )
                    )
                return {
                    "token_type": body.get("token_type"),
                    "access_token": body.get("access_token"),
                }
    except asyncio.TimeoutError:
        raise _RefreshOauth2TokenError(
            I18nMessage.TODO_i18n("Timeout during OAuth2 token refresh")
        )
    except aiohttp.ClientError as err:
        raise _RefreshOauth2TokenError(
            I18nMessage.TODO_i18n(
                "HTTP error during OAuth2 token refresh: %s" % str(err)
            )
        )


@prepare_secret.register(ParamSpecSecret.Logic.Oauth2)
async def prepare_secret_oauth2(
    logic: ParamSpecSecret.Logic.Oauth2, value: UserProvidedSecret
) -> ModuleSecret:
    """
    Prepare an OAuth2 secret for a module fetch() call.

    SECURITY: the module will get an access token to authenticate as the user.
    Some services (Google) support refresh tokens: for those, the module will
    get a _temporary_ token (that may last 1hr). Other services (Intercom) do
    not support refresh tokens, so the module will be able to authenticate with
    the provider as the end user forever.

    A non-`None` UserProvidedSecret has a "secret" sub-dict with keys:

        * `"token_type"`: token type (unset implies `"Bearer"`)
        * `"access_token"`: token that might expire, provided by service.
        * `"refresh_token"`: provided by some services (Google) so we can
                             give modules a temporary token.

    On success, ModuleSecret "secret" sub-dict will have keys:

        * `"token_type"`: token type (expect `"Bearer"`)
        * `"access_token"`: OAuth 2.0 token

    Otherwise, ModuleSecret "error" value will be an I18nMessage-compatible
    dict describing the problem.

    All problems that may cause an "error":

        * After the user set a valid secret, Workbench was reconfigured and the
          provider was disabled.
        * There was an HTTP error refreshing the token.
        * There was an error parsing the server's refresh-token response.
        * TODO list (and translate) special cases of HTTP error (e.g.,
          HTTP 400 `{"error": "invalid_grant", ...}`)
    """
    if not value:
        return None

    service: oauth.OAuth2 = oauth.OAuthService.lookup_or_none(logic.service)
    if not service:
        return _secret_error(
            value,
            I18nMessage.TODO_i18n("Service %r is no longer configured" % logic.service),
        )

    token = value.get("secret", {})
    if "refresh_token" in token:
        try:
            token = await _refresh_oauth2_token(service, token["refresh_token"])
        except _RefreshOauth2TokenError as err:
            return _secret_error(value, err.i18n_message)

    return {
        **value,
        "secret": {
            "token_type": token.get("token_type", ""),
            "access_token": token.get("access_token", ""),
        },
    }


@prepare_secret.register(ParamSpecSecret.Logic.String)
async def prepare_secret_string(
    logic: ParamSpecSecret.Logic.String, value: UserProvidedSecret
) -> ModuleSecret:
    """
    Prepare a String secret for a module fetch() call.

    SECURITY: the module will get the user-input value.

    A non-`None` UserProvidedSecret has a "secret" str.

    A returned ModuleSecret "secret" will be the same "secret" str.

    There are no errors.
    """
    return value
