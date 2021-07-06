import json
import os
import os.path
from typing import Dict, Optional

from .util import DJANGO_ROOT

__all__ = ("OAUTH_SERVICES",)

# Third party services
OAUTH_SERVICES: Dict[str, Dict[str, Optional[str]]] = {}
"""service => parameters. See requests-oauthlib docs"""


def _maybe_load_oauth_service(
    name: str, env_var_name: str, default_path_name: str, parse
):
    path = os.environ.get(env_var_name)
    if not path:
        path = os.path.join(DJANGO_ROOT, default_path_name)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        # This is normal: frontend+fetcher get OAuth, but cron+renderer do not
        return
    config = parse(data)
    OAUTH_SERVICES[name] = config


# Google, for Google Drive module
def _parse_google_oauth(d):
    return {
        "class": "OAuth2",
        "client_id": d["web"]["client_id"],
        "client_secret": d["web"]["client_secret"],
        "auth_url": d["web"]["auth_uri"],
        "token_url": d["web"]["token_uri"],
        "refresh_url": d["web"]["token_uri"],
        "redirect_url": d["web"]["redirect_uris"][0],
        "scope": " ".join(
            [
                "openid",
                "https://www.googleapis.com/auth/drive.readonly",
                "https://www.googleapis.com/auth/userinfo.email",
            ]
        ),
    }


_maybe_load_oauth_service(
    "google", "CJW_GOOGLE_CLIENT_SECRETS", "client_secret.json", _parse_google_oauth
)

# Intercom, for Intercom module
def _parse_intercom_oauth(d):
    return {
        "class": "OAuth2",
        "client_id": d["client_id"],
        "client_secret": d["client_secret"],
        "auth_url": "https://app.intercom.com/oauth",
        "token_url": "https://api.intercom.io/auth/eagle/token",
        "refresh_url": None,
        "redirect_url": d["redirect_url"],
        "scope": "",  # set on Intercom app, not in our request
    }


_maybe_load_oauth_service(
    "intercom",
    "CJW_INTERCOM_CLIENT_SECRETS",
    "intercom_secret.json",
    _parse_intercom_oauth,
)

# Twitter, for Twitter module
def _parse_twitter_oauth(d):
    return {
        "class": "OAuth1a",
        "consumer_key": d["key"],
        "consumer_secret": d["secret"],
        "auth_url": "https://api.twitter.com/oauth/authorize",
        "request_token_url": "https://api.twitter.com/oauth/request_token",
        "access_token_url": "https://api.twitter.com/oauth/access_token",
        "redirect_url": d["redirect_url"],
    }


_maybe_load_oauth_service(
    "twitter", "CJW_TWITTER_CLIENT_SECRETS", "twitter_secret.json", _parse_twitter_oauth
)
