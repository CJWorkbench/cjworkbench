from babel.messages.catalog import Catalog
from contextlib import contextmanager
from typing import Dict
from cjworkbench.i18n.trans import MESSAGE_LOCALIZER_REGISTRY, MessageLocalizer
from unittest.mock import patch


@contextmanager
def mock_app_catalogs(catalogs: Dict[str, Catalog]):
    def mock_for_application(registry):
        return MessageLocalizer(catalogs)

    with patch(
        "cjworkbench.i18n.trans.MessageLocalizerRegistry.for_application",
        mock_for_application,
    ):
        yield


@contextmanager
def mock_cjwmodule_catalogs(catalogs: Dict[str, Catalog]):
    def mock_for_cjwmodule(registry):
        return MessageLocalizer(catalogs)

    with patch(
        "cjworkbench.i18n.trans.MessageLocalizerRegistry.for_cjwmodule",
        mock_for_cjwmodule,
    ):
        yield
