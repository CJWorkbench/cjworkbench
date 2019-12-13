from babel.messages.pofile import read_po, write_po
from babel.messages.catalog import Catalog, Message
from typing import Optional, FrozenSet, Any, Union, Tuple
import pathlib

MessageUID = Union[str, Tuple[str, str]]


def message_unique_identifier(message: Message) -> MessageUID:
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


def remove_strings(catalog: Catalog):
    """ Convert the text of all messages (except header) to empty string.
    """
    for message in catalog:
        if message.id:
            message.string = ""


def find_fuzzy_messages(
    *, old_catalog: Catalog, new_catalog: Catalog
) -> FrozenSet[MessageUID]:
    """ Compare two catalogs to find fuzzy messages

    A message string of the new catalog will be marked as fuzzy iff 
    the corresponding message of the old catalog is non-empty and different.
    
    Notice that fuzziness in the old catalog will be ignored.
    """
    fuzzy = set()
    for message in new_catalog:
        if message.id:
            old_message = find_corresponding_message(old_catalog, message)
            if old_message and old_message.string != message.string:
                fuzzy.add(message_unique_identifier(message))
    return frozenset(fuzzy)


def fill_catalog(
    target_catalog: Catalog,
    id_source_catalog: Catalog,
    string_source_catalog: Catalog = Catalog(),
):
    """ Add messages to target_catalog

    Every property of the message will be taken from id_source_catalog,
    except for its string which will be taken 
      - from string_source_catalog if not empty
      - else from target_catalog itself
    """
    for message in id_source_catalog:
        if message.id:  # ignore header
            new_string = (
                find_corresponding_string(string_source_catalog, message)
                or find_corresponding_string(target_catalog, message)
                or ""
            )
            target_catalog[message.id] = message
            target_catalog[message.id].string = new_string


def mark_fuzzy(
    catalog: Catalog, fuzzy: FrozenSet[MessageUID], old_catalog: Catalog = Catalog()
):
    """ Mark messages in catalog as fuzzy

    A message string of the resulting catalog will be marked as fuzzy if 
     - it was fuzzy in old_catalog, or
     - it is non-empty and its unique identifier (in the sense of `message_unique_identifier`) is in `fuzzy`.
    """
    for message in catalog:
        if message.id:  # ignore header
            old_message = find_corresponding_message(old_catalog, message)
            if (old_message and old_message.fuzzy) or (
                message.string and message_unique_identifier(message) in fuzzy
            ):
                message.flags.add("fuzzy")


def read_po_catalog(filename: str) -> Catalog:
    """ Try to read a po catalog from the given path.
    Throw on failure.
    """
    with open(filename, "r") as catalog_file:
        return read_po(catalog_file)


def write_po_catalog(filename: Union[str, pathlib.Path], catalog: Catalog, **kwargs):
    """ Try to write a po catalog to the given path.
    Throw on failure.
    """
    pathlib.Path(filename).parent.mkdir(parents=True, exist_ok=True)
    with open(filename, "wb") as catalog_file:
        write_po(catalog_file, catalog, **kwargs)
