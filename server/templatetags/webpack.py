import functools
import json
import logging
import time
from pathlib import Path

from django import template
from django.conf import settings

register = template.Library()

logger = logging.getLogger(__name__)


_MANIFEST_PATH = (
    Path(__file__).parent.parent.parent / "assets" / "bundles" / "webpack-manifest.json"
)


def _load_manifest_inner():
    with open(_MANIFEST_PATH) as f:
        return json.load(f)


if settings.DEBUG:

    def _load_manifest():
        for i in range(50 * 20):
            try:
                return _load_manifest_inner()
            except FileNotFoundError:
                if i % 50 == 0:
                    logging.info(
                        "Waiting for manifest to appear at %s...", str(_MANIFEST_PATH)
                    )
                time.sleep(0.1)
        return _load_manifest()


else:
    _load_manifest = functools.lru_cache(maxsize=None)(_load_manifest_inner)


@register.simple_tag
def bundle_path(name: str):
    manifest = _load_manifest()
    path = manifest[name]
    return "%sbundles/%s" % (settings.STATIC_URL, path)
