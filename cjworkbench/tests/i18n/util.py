from babel.messages.catalog import Catalog
from contextlib import contextmanager
from typing import Dict
from cjworkbench.i18n.trans import (
    MESSAGE_LOCALIZER_REGISTRY,
    MessageLocalizer,
    MessageCatalogsRegistry,
)
from cjwstate.modules.types import ModuleZipfile
import pathlib


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


@contextmanager
def mock_module_catalogs(module_id: str, catalogs: Dict[str, Catalog]):
    # Code to acquire resource, e.g.:
    with MESSAGE_LOCALIZER_REGISTRY._module_localizers_lock:
        old_supported_modules = MESSAGE_LOCALIZER_REGISTRY._supported_modules
        old_module_localizers = MESSAGE_LOCALIZER_REGISTRY._module_localizers
    try:
        module_zipfile = ModuleZipfile(pathlib.Path(f"{module_id}.123456.zip"))
        new_localizer = MessageLocalizer(MessageCatalogsRegistry(catalogs))
        with MESSAGE_LOCALIZER_REGISTRY._module_localizers_lock:
            MESSAGE_LOCALIZER_REGISTRY._supported_modules[module_id] = module_zipfile
            MESSAGE_LOCALIZER_REGISTRY._module_localizers[
                module_zipfile
            ] = new_localizer
        yield new_localizer
    finally:
        # Code to release resource:
        with MESSAGE_LOCALIZER_REGISTRY._module_localizers_lock:
            MESSAGE_LOCALIZER_REGISTRY._supported_modules = old_supported_modules
            MESSAGE_LOCALIZER_REGISTRY._module_localizers = old_module_localizers
