from babel.messages.catalog import Catalog
from typing import Dict
from cjworkbench.i18n.trans import MESSAGE_LOCALIZER_REGISTRY, MessageLocalizer
from unittest.mock import patch


def mock_app_catalogs(catalogs: Dict[str, Catalog]):
    return patch.object(
        MODULE_LOCALIZER_REGISTRY, "application_localizer", MessageLocalizer(catalogs)
    )


@contextmanager
def mock_cjwmodule_catalogs(catalogs: Dict[str, Catalog]):
    return patch.object(
        MODULE_LOCALIZER_REGISTRY, "cjwmodule_localizer", MessageLocalizer(catalogs)
    )
