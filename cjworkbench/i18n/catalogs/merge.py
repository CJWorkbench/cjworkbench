from babel.messages.catalog import Catalog
from cjworkbench.i18n import default_locale, supported_locales
from cjworkbench.i18n.catalogs.util import (
    find_corresponding_string,
    find_corresponding_message,
    read_po_catalog,
    write_po_catalog,
    message_unique_identifier,
)
from cjworkbench.i18n.catalogs import (
    catalog_path,
    CATALOG_FILENAME,
    TEMPLATE_CATALOG_FILENAME,
    COMMENT_TAG_FOR_DEFAULT_MESSAGE,
)
import re
import sys
from os import remove
from shutil import copyfile


MID_EXTRACT_CATALOG_FILENAME = "old.po"


_default_message_re = re.compile(
    r"\s*" + COMMENT_TAG_FOR_DEFAULT_MESSAGE + ":\s*(.*)\s*"
)


def prepare():
    """ Backup the catalogs for usage while merging
    
    When lingui scans the code, it comments out any messages of the catalog that are not in the js code.
    This requires special care in order not to lose any already translated content for non-default locales,
    something that is made worse by the fact that 
    commented out messages do not support context (neither in lingui nor in pybabel)
    
    This will not be required in version 3 of lingui: 
    it will give the ability to define multiple message catalogs 
    that will be merged during its compilation step,
    some of which can be managed externally.
    In that case, we would keep two separate message catalogs for source messages
    (one for messages parsed by lingui and one for messages parsed by pybabel) 
    and compile them both for js (with lingui)
    and for babel (just merge its own source catalog with the source catalog of lingui).
    
    Moreover, we want to mark messages whose default value has changed as fuzzy.
    This requires to know their previous default value (in the default locale message file)
    as well as their current one.
    """
    print("Preparing extraction of python files")
    for locale in supported_locales:
        copyfile(
            catalog_path(locale, CATALOG_FILENAME),
            catalog_path(locale, MID_EXTRACT_CATALOG_FILENAME),
        )


def merge():
    """ Merge the messages found in the template catalog of the default locale into the catalogs of all locales.
    
    The template catalog is searched for special comments that indicate default messages.
    These messages are added to the catalog for the default locale.
    
    We compare the old and new default messages.
    If they are (non-empty and) different, we will mark them as fuzzy in message catalogs (of non-default locales).
    """
    (python_source_catalog, fuzzy) = _merge_source_catalog()
    print("Found %s new fuzzy messages" % len(fuzzy))
    for locale in supported_locales:
        if locale != default_locale:
            _merge_catalog(locale, python_source_catalog, fuzzy)


def _merge_source_catalog():
    """ Read the message files extracted from js and python for the default locale and merge them.
    
    Return 
        - a catalog with the new messages extracted from python code
        - a set with the unique identifiers (in the sense of `message_unique_identifier`) of fuzzy messages
    """
    target_catalog_path = catalog_path(default_locale, CATALOG_FILENAME)
    print("Merging catalog for %s at %s" % (default_locale, target_catalog_path))
    old_source_catalog = read_po_catalog(
        catalog_path(default_locale, MID_EXTRACT_CATALOG_FILENAME)
    )
    js_catalog = read_po_catalog(catalog_path(default_locale, CATALOG_FILENAME))
    fuzzy = set()
    # Find fuzzy in js translations
    for message in js_catalog:
        if message.id:
            if find_corresponding_string(old_source_catalog, message) != message.string:
                fuzzy.add(message_unique_identifier(message))

    # Update default messages in python translations and find fuzzy
    python_catalog = read_po_catalog(
        catalog_path(default_locale, TEMPLATE_CATALOG_FILENAME)
    )
    for message in python_catalog:
        if message.id:
            for comment in message.auto_comments:
                match = _default_message_re.match(comment)
                if match:
                    default_message = match.group(1).strip()
                    message.auto_comments.remove(comment)
                    message.string = default_message

            if find_corresponding_string(old_source_catalog, message) != message.string:
                fuzzy.add(message_unique_identifier(message))
            js_catalog[message.id] = message

    write_po_catalog(
        catalog_path(default_locale, CATALOG_FILENAME), js_catalog, ignore_obsolete=True
    )
    return (python_catalog, frozenset(fuzzy))


def _merge_catalog(locale: str, source_catalog: Catalog, fuzzy: set = set()):
    """ Add the messages of `source_catalog` in the catalog for `locale` and write the result to a file.

    Message strings will be populated using backup catalogs.
    
    A message string of the resulting catalog will be marked as fuzzy if 
     - it was fuzzy before, or
     - it is non-empty and its unique identifier (in the sense of `message_unique_identifier`) is in `fuzzy`.
    """
    target_catalog_path = catalog_path(locale, CATALOG_FILENAME)
    print("Merging catalog for %s at %s" % (locale, target_catalog_path))
    catalog = read_po_catalog(target_catalog_path)
    old = read_po_catalog(catalog_path(locale, MID_EXTRACT_CATALOG_FILENAME))

    for message in source_catalog:
        if message.id:  # ignore header
            if find_corresponding_message(old, message):
                message.string = find_corresponding_string(old, message)
            catalog[message.id] = message
    for message in catalog:
        if message.id:  # ignore header
            old_message = find_corresponding_message(old, message)
            if (old_message and old_message.fuzzy) or (
                message.string and message_unique_identifier(message) in fuzzy
            ):
                message.flags.add("fuzzy")

    write_po_catalog(target_catalog_path, catalog, ignore_obsolete=True)


def clean():
    """ Remove backup catalogs created by `prepare` and convert the catalog of the default locale to a template catalog

    The strings of messages in the catalog of the default locale are added to the template catalog as special comments.
    """
    print("Cleaning up")
    # Remove temp files
    for locale in supported_locales:
        remove(catalog_path(locale, MID_EXTRACT_CATALOG_FILENAME))

    # Update template file for default locale
    catalog = read_po_catalog(catalog_path(default_locale, CATALOG_FILENAME))
    for message in catalog:
        message.auto_comments.append(
            COMMENT_TAG_FOR_DEFAULT_MESSAGE + ": " + message.string
        )
        message.string = ""
    write_po_catalog(
        catalog_path(default_locale, TEMPLATE_CATALOG_FILENAME),
        catalog,
        ignore_obsolete=True,
        width=10000000,  # we set a huge value for width, so that special comments do not wrap
        omit_header=True,
    )


def main(mode):
    if mode == "prepare":
        prepare()
    elif mode == "merge":
        merge()
        clean()
    else:
        print(
            """ 
        You must provide one of the following arguments:
            - "prepare": backups the current catalog, in order to prepare for extraction by lingui
            
            - "merge": merges the messages extracted by lingui and by pybabel into the catalogs created by lingui, 
               using the backups created by prepare as a source of translations for non-default languages;
               then, cleans the backups
        """
        )


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else None
    main(mode)
