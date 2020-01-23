from babel.messages.pofile import read_po, write_po
from babel.messages.catalog import Catalog, Message
from typing import Optional, FrozenSet, Union, Tuple
import pathlib

MessageUID = Union[str, Tuple[str, str]]


def message_unique_identifier(message: Message) -> MessageUID:
    """ Return an immutable element that uniquely identifies a message.
    Usually, messages are identified by their ID, 
    but if they have a context it must also be taken into account.
    """
    return message.id if not message.context else (message.id, message.context)


def find_message(
    catalog: Catalog, message_id: str, context: Optional[str] = None
) -> Optional[Message]:
    message = catalog.get(message_id, context=context)
    return message if message else None


def find_string(
    catalog: Catalog, message_id: str, context: Optional[str] = None
) -> Optional[Message]:
    message = find_message(catalog, message_id, context=context)
    return message.string if message else None


def find_corresponding_message(catalog: Catalog, message: Message) -> Optional[Message]:
    """ Search the catalog for a message with the same ID (and context) and return it.
    """
    return find_message(catalog, message.id, context=message.context)


def find_corresponding_string(catalog: Catalog, message: Message) -> Optional[str]:
    """ Search the catalog for a message with the same ID (and context) and return its string.
    """
    return find_string(catalog, message.id, context=message.context)


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


def copy_message(message: Message, **kwargs) -> Message:
    """Copies a message, replacing any of its attributes given in kwargs
    """
    return Message(
        **{
            "id": kwargs.get("id", message.id),
            "context": kwargs.get("context", message.context),
            "string": kwargs.get("string", message.string),
            "flags": kwargs.get("flags", message.flags),
            "locations": kwargs.get("locations", message.locations),
            "user_comments": kwargs.get("user_comments", message.user_comments),
            "auto_comments": kwargs.get("auto_comments", message.auto_comments),
        }
    )


def add_or_update_message(catalog: Catalog, message: Message):
    if find_corresponding_message(catalog, message):
        catalog.delete(message.id, context=message.context)
    catalog[message.id] = message


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
      
    Only target catalog is modified
    """
    for message in id_source_catalog:
        if message.id:  # ignore header
            new_string = (
                find_corresponding_string(string_source_catalog, message)
                or find_corresponding_string(target_catalog, message)
                or ""
            )
            add_or_update_message(
                target_catalog, copy_message(message, string=new_string)
            )


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


def catalogs_are_same(catalog_1: Catalog, catalog_2: Catalog) -> bool:
    return (
        catalog_1.locale == catalog_2.locale
        and catalog_included_in(catalog_1, catalog_2)
        and catalog_included_in(catalog_2, catalog_1)
    )


def messages_are_same(message: Message, other_message: Message) -> bool:
    return (
        message == other_message  # this compares id and context
        and message.string == other_message.string
        and message.flags == other_message.flags
        and message.auto_comments == other_message.auto_comments
        and message.user_comments == other_message.user_comments
        and message.locations == other_message.locations
    )


def catalog_included_in(catalog: Catalog, other_catalog: Catalog) -> bool:
    for message in catalog:
        if message.id:  # ignore header
            other_message = find_corresponding_message(other_catalog, message)
            if other_message:
                if not messages_are_same(message, other_message):
                    return False
            else:
                return False
    return True


def read_po_catalog(filename: str) -> Catalog:
    """ Try to read a po catalog from the given path.
    Throw on failure.
    """
    with open(filename, "r") as catalog_file:
        return read_po(catalog_file)


def write_po_catalog(filename: Union[str, pathlib.Path], catalog: Catalog, **kwargs):
    """ Try to write a po catalog to the given path.
    Build the directories and the file mentioned in the path if they do not exist.
    Throw on failure.
    """
    # Build parent directories if needed
    pathlib.Path(filename).parent.mkdir(parents=True, exist_ok=True)

    # Write the file
    with open(filename, "wb") as catalog_file:
        write_po(catalog_file, catalog, **kwargs)
