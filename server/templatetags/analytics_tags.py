from django import template
from server.utils import get_intercom_app_id, get_google_analytics_id

register = template.Library()

@register.simple_tag
def intercom_id():
    return get_intercom_app_id()

@register.simple_tag
def google_analytics_id():
    return get_google_analytics_id()

