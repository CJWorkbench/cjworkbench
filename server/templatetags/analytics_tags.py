import hashlib
import hmac
import os
from typing import Any, Dict, Optional

from cjwkernel.util import json_encode
from django.conf import settings
from django.contrib.auth.models import User
from django import template

register = template.Library()

# return analytics IDs if they are set
INTERCOM_LAYOUT_SETTINGS = dict(
    alignment="right", horizontal_padding=30, vertical_padding=20
)


@register.simple_tag
def heap_analytics_id() -> Optional[str]:
    return os.environ.get("CJW_HEAP_ANALYTICS_ID")


@register.simple_tag
def google_analytics_id() -> Optional[str]:
    return os.environ.get("CJW_GOOGLE_ANALYTICS")


@register.simple_tag(takes_context=True)
def intercom_settings(context) -> Optional[Dict[str, Any]]:
    if not settings.INTERCOM_APP_ID:
        return None

    user = context["user"]
    if user.is_anonymous:
        return dict(app_id=settings.INTERCOM_APP_ID, **INTERCOM_LAYOUT_SETTINGS)

    ret = dict(
        app_id=settings.INTERCOM_APP_ID,
        user_id=str(user.id),
        name=(user.first_name + " " + user.last_name).strip(),
        email=user.email,
        created_at=int(user.date_joined.timestamp()),
    )

    if settings.INTERCOM_IDENTITY_VERIFICATION_SECRET:
        ret["user_hash"] = hmac.new(
            settings.INTERCOM_IDENTITY_VERIFICATION_SECRET.encode("ascii"),
            str(user.id).encode("ascii"),
            digestmod=hashlib.sha256,
        ).hexdigest()

    ret.update(INTERCOM_LAYOUT_SETTINGS)
    return ret
