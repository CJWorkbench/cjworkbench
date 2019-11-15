from babel.messages.pofile import read_po, write_po
from babel.messages.catalog import Catalog, Message
from typing import Optional


def message_unique_identifier(message: Message):
    """ Return an immutable element that uniquely identifies a message.
    Usually, messages are identified by their ID, 
    but if they have a context it must also be taken into account.
    """
    return message.id if not message.context else (message.id, message.context)


def find_corresponding_message(catalog: Catalog, message: Message) -> Optional[Message]:
    """ Search the catalog for a message with the same ID (and context) and return it.
    """
    message = catalog.get(message.id, context=message.context)
    return message if message else None


def find_corresponding_string(catalog: Catalog, message: Message) -> Optional[str]:
    """ Search the catalog for a message with the same ID (and context) and return its string.
    """
    corresponding_message = find_corresponding_message(catalog, message)
    return corresponding_message.string if corresponding_message else None


def read_po_catalog(filename: str) -> Catalog:
    """ Try to read a po catalog from the given path.
    Throw on failure.
    """
    with open(filename, "r") as catalog_file:
        return read_po(catalog_file)


def write_po_catalog(filename: str, catalog: Catalog, **kwargs):
    """ Try to write a po catalog to the given path.
    Throw on failure.
    """
    with open(filename, "wb") as catalog_file:
        write_po(catalog_file, catalog, **kwargs)
