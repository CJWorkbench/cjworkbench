"""Helpers with OAuth 1.0a and OAuth 2.0 sign-ins.

This lets us get offline access tokens for Twitter and Google Drive. Our
modules use these tokens to download data.

At this module's level of abstraction:

    * A `service_id` references a service in `settings.py`
    * `generate_redirect` returns a (url, state) pair.
    * `receive_code` returns a long-term token.
    * `generate_short_term_token` returns a short-term token.
"""

from django.conf import settings
from typing import Union

def get_service(service_id: str) -> Union[OAuthService,HttpResponse]:
    """Return an OAuthHelper (if service is configured) or HttpResponse error.
    """
    if service_id in settings.PARAMETER_OAUTH_SERVICES:
        return OAuthService
