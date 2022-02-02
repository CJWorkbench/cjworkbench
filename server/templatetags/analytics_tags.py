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
