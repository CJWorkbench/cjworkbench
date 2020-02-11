from os import path
from babel.messages.pofile import read_po
from babel.messages.catalog import Catalog
from cjworkbench.i18n import supported_locales
from functools import lru_cache


CATALOG_FILENAME = "messages.po"
TEMPLATE_CATALOG_FILENAME = "messages.pot"

COMMENT_TAG_FOR_DEFAULT_MESSAGE = "default-message"


def catalog_path(locale_id: str, catalog: str = CATALOG_FILENAME) -> str:
    """ Return the path of the given catalog for the given locale
    
    The catalog argument is supposed to be the filename of the catalog file,
    e.g. CATALOG_FILENAME or TEMPLATE_CATALOG_FILENAME
    """
    return path.join("assets", "locale", locale_id, catalog)
