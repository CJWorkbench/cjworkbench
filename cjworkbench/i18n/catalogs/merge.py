from babel.messages.pofile import read_po, write_po
from cjworkbench.i18n import default_locale, supported_locales
from cjworkbench.i18n.catalogs import (
    catalog_path,
    CATALOG_FILENAME,
    BACKUP_CATALOG_FILENAME,
    TEMPLATE_CATALOG_FILENAME,
    COMMENT_TAG_FOR_DEFAULT_MESSAGE,
)
import re
import sys
from os import remove
from shutil import copyfile

_default_message_re = re.compile(
    r"\s*" + COMMENT_TAG_FOR_DEFAULT_MESSAGE + ":\s*(.*)\s*"
)


def prepare():
    """ Backup the catalogs of non-default locales
    
    When lingui scans the code, it comments out any messages of the catalog that are not in the js code.
    This requires special care in order not to lose any already translated content,
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
    """
    print("Preparing extraction of python files")
    for locale in supported_locales:
        if locale != default_locale:
            copyfile(
                catalog_path(locale, CATALOG_FILENAME),
                catalog_path(locale, BACKUP_CATALOG_FILENAME),
            )


def _merge_catalog(locale, source_catalog, default={}):
    """ Add the messages of `source_catalog` in the catalog for `locale`.

    If `default` is not empty, message strings will be populated using the data in `default` 
    TODO: make `default` support context
    else, message strings will be populated using backup catalogs.
    
    The intention is that the default locale will take strings from special comments in the template catalog,
    while the other locales will take their strings from the backup.    
    """
    target_catalog_path = catalog_path(locale, CATALOG_FILENAME)
    print("Merging catalog for %s at %s" % (locale, target_catalog_path))
    with open(target_catalog_path, "r") as target_catalog_file:
        catalog = read_po(target_catalog_file)
    if not default:
        with open(
            catalog_path(locale, BACKUP_CATALOG_FILENAME), "r"
        ) as target_catalog_file:
            old = read_po(target_catalog_file)
    for message in source_catalog:
        if message.id:  # ignore header
            string = ""
            if default and message.id in default:
                message.string = default[message.id]
            elif old and old.get(message.id, context=message.context):
                message.string = old.get(message.id, context=message.context).string
            catalog[message.id] = message
    with open(target_catalog_path, "wb") as target_catalog_file:
        write_po(target_catalog_file, catalog, ignore_obsolete=True)


def merge():
    """ Merge the messages found in the template catalog of the default locale into the catalogs of all locales.
    
    The template catalog is searched for special comments that indicate default messages.
    These messages are added to the catalog for the default locale.
    """
    source_catalog_path = catalog_path(default_locale, TEMPLATE_CATALOG_FILENAME)
    with open(source_catalog_path) as source_catalog_file:
        source_catalog = read_po(source_catalog_file)
    default_messages = {}
    print("Reading source locale pot file at %s" % source_catalog_path)
    for message in source_catalog:
        for comment in message.auto_comments:
            match = _default_message_re.match(comment)
            if match:
                default_messages[message.id] = match.group(1).strip()
                message.auto_comments.remove(comment)
    for locale in supported_locales:
        if locale != default_locale:
            _merge_catalog(locale, source_catalog)
    _merge_catalog(default_locale, source_catalog, default_messages)


def clean():
    """ Remove backup catalogs created by `prepare` and convert the catalog of the default locale to a template catalog

    The strings of messages in the catalog of the default locale are added to the template catalog as special comments.
    """
    print("Cleaning up")
    # Remove temp files for non-default locales
    for locale in supported_locales:
        if locale != default_locale:
            remove(catalog_path(locale, BACKUP_CATALOG_FILENAME))

    # Update template file for default locale
    with open(catalog_path(default_locale, CATALOG_FILENAME)) as catalog_file:
        catalog = read_po(catalog_file)
    for message in catalog:
        message.auto_comments.append(
            COMMENT_TAG_FOR_DEFAULT_MESSAGE + ": " + message.string
        )
        message.string = ""
    with open(
        catalog_path(default_locale, TEMPLATE_CATALOG_FILENAME), "wb"
    ) as source_catalog_file:
        write_po(
            source_catalog_file,
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
