from typing import Dict

from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def workbench_config() -> Dict[str, str]:
    return dict(
        help_email=settings.HELP_EMAIL,
        help_mailto="mailto:" + settings.HELP_EMAIL,
    )
