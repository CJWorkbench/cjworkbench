from django import template
import os

register = template.Library()

# return analytics IDs if they are set
# TODO move these env-variable handlers to settings.py


@register.simple_tag
def load_analytics_ids():
    """Return analytics IDs as a dict.

    Keys:

    * `intercom_id`
    * `google_analytics_id`
    * `heap_analytics_id`
    """
    return {
        "intercom_id": os.environ.get("CJW_INTERCOM_APP_ID"),
        "google_analytics_id": os.environ.get("CJW_GOOGLE_ANALYTICS"),
        "heap_analytics_id": os.environ.get("CJW_HEAP_ANALYTICS_ID"),
    }
