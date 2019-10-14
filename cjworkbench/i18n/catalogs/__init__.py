from os import path

CATALOG_FILENAME = "messages.po"
BACKUP_CATALOG_FILENAME = "old.po"
TEMPLATE_CATALOG_FILENAME = "messages.pot"

COMMENT_TAG_FOR_DEFAULT_MESSAGE = "default-message"


def catalog_path(locale: str, catalog: str) -> str:
    return path.join("assets", "locale", locale, catalog)
