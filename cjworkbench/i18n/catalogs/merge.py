from babel.messages.catalog import Catalog
from cjworkbench.i18n import default_locale, supported_locales
from cjworkbench.i18n.catalogs.util import (
    read_po_catalog,
    write_po_catalog,
    find_fuzzy_messages,
    fill_catalog,
    mark_fuzzy,
    remove_strings,
    new_catalog_from_metadata,
    move_strings_to_comments,
)
from cjworkbench.i18n.catalogs import (
    catalog_path,
    CATALOG_FILENAME,
    TEMPLATE_CATALOG_FILENAME,
    COMMENT_TAG_FOR_DEFAULT_MESSAGE,
)
from os import remove
import re
from shutil import copyfile
import sys
from typing import List, FrozenSet


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
    # First, merge the js and python catalogs for the default locale and find fuzzy messages
    print(
        "Merging catalog for %s at %s"
        % (default_locale, catalog_path(default_locale, CATALOG_FILENAME))
    )
    old_source_catalog = read_po_catalog(
        catalog_path(default_locale, MID_EXTRACT_CATALOG_FILENAME)
    )
    js_catalog = read_po_catalog(catalog_path(default_locale, CATALOG_FILENAME))

    python_catalog = read_po_catalog(
        catalog_path(default_locale, TEMPLATE_CATALOG_FILENAME)
    )

    (catalog, python_source_catalog, fuzzy) = _merge_source_catalog(
        js_catalog, python_catalog, old_source_catalog
    )

    write_po_catalog(
        catalog_path(default_locale, CATALOG_FILENAME), catalog, ignore_obsolete=True
    )
    print("Found %s new fuzzy messages" % len(fuzzy))

    # Then, add the new python messages to the catalogs for the other locales and mark fuzzy messages
    for locale in supported_locales:
        if locale != default_locale:
            target_catalog_path = catalog_path(locale, CATALOG_FILENAME)
            print("Merging catalog for %s at %s" % (locale, target_catalog_path))
            js_catalog = read_po_catalog(target_catalog_path)
            old = read_po_catalog(catalog_path(locale, MID_EXTRACT_CATALOG_FILENAME))

            catalog = _merge_catalogs([js_catalog, python_source_catalog], old, fuzzy)

            write_po_catalog(target_catalog_path, catalog, ignore_obsolete=True)


def _merge_source_catalog(js_catalog, python_catalog, old_source_catalog):
    """ Read the message catalogs extracted from js and python for the default locale and merge them.
    
    Return 
        - the new merged catalog for the default locale
        - a catalog with the new messages extracted from python code
        - a set with the unique identifiers (in the sense of `message_unique_identifier`) of fuzzy messages
    """

    for message in python_catalog:
        if message.id:
            for comment in message.auto_comments:
                match = _default_message_re.match(comment)
                if match:
                    default_message = match.group(1).strip()
                    message.auto_comments.remove(comment)
                    message.string = default_message

    fill_catalog(js_catalog, python_catalog, python_catalog)

    return (
        js_catalog,
        python_catalog,
        find_fuzzy_messages(new_catalog=js_catalog, old_catalog=old_source_catalog),
    )


def _merge_catalogs(catalogs: List[Catalog], old: Catalog, fuzzy: FrozenSet):
    """
    Merge `catalogs` into one big catalog.

    Message strings will be populated using the `old` catalog.

    The strings in `catalogs` must be either empty or in the same language as
    `old`.

    A message string of the resulting catalog will be marked as fuzzy if:

    * it was fuzzy in the `old` catalog; or
    * it is non-empty and its unique identifier (in the sense of
      `message_unique_identifier`) is in `fuzzy`
    """

    ret = new_catalog_from_metadata(old)
    for catalog in catalogs:
        fill_catalog(ret, catalog, old)
    mark_fuzzy(ret, fuzzy, old)

    return ret


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
    move_strings_to_comments(catalog, comment_tag=COMMENT_TAG_FOR_DEFAULT_MESSAGE)
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
