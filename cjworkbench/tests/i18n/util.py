from babel.messages.catalog import Catalog
from contextlib import contextmanager
from typing import Dict
from cjworkbench.i18n.trans import (
    MESSAGE_LOCALIZER_REGISTRY,
    MessageLocalizer,
    MessageCatalogsRegistry,
)


@contextmanager
def mock_app_catalogs(catalogs: Dict[str, Catalog]):
    # Code to acquire resource, e.g.:
    old_localizer = MESSAGE_LOCALIZER_REGISTRY._app_localizer
    try:
        new_localizer = MessageLocalizer(MessageCatalogsRegistry(catalogs))
        MESSAGE_LOCALIZER_REGISTRY._app_localizer = new_localizer
        yield new_localizer
    finally:
        # Code to release resource:
        MESSAGE_LOCALIZER_REGISTRY._app_localizer = old_localizer
