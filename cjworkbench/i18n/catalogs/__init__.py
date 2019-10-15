from os import path
from babel.messages.pofile import read_po
from babel.messages.catalog import Catalog
from cjworkbench.i18n.exceptions import UnsupportedLocaleError, BadCatalogsError
from cjworkbench.i18n import supported_locales
from functools import lru_cache


CATALOG_FILENAME = "messages.po"
TEMPLATE_CATALOG_FILENAME = "messages.pot"

COMMENT_TAG_FOR_DEFAULT_MESSAGE = "default-message"


@lru_cache(maxsize=len(supported_locales))
def load_catalog(locale: str) -> Catalog:
    """ Load the message catalog for the given locale into memory
    """
    try:
        with open(catalog_path(locale, CATALOG_FILENAME)) as catalog_file:
            return read_po(catalog_file)
    except ValueError as error:
        raise BadCatalogsError(
            "The catalog for the given locale (%s) is badly formatted" % locale
        ) from error
    except Exception as error:
        raise UnsupportedLocaleError(
            "Can't load a catalog for the given locale (%s)" % locale
        ) from error


def catalog_path(locale: str, catalog: str) -> str:
    """ Return the path of the given catalog for the given locale
    
    The catalog argument is supposed to be the filename of the catalog file,
    e.g. CATALOG_FILENAME or TEMPLATE_CATALOG_FILENAME
    """
    return path.join("assets", "locale", locale, catalog)
