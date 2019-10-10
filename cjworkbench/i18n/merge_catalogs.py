from babel.messages.pofile import read_po, write_po
from cjworkbench.i18n import default_locale, supported_locales, catalog_path
import re
import sys
from os import remove
from shutil import copyfile

_default_message_re = re.compile(r"\s*default-message:\s*(.*)\s*")


def prepare():
    print("Preparing extraction of python files")
    for locale in supported_locales:
        if locale != default_locale:
            copyfile(catalog_path(locale), catalog_path(locale, "old.po"))


def _merge_catalog(locale, source_catalog, default={}):
    target_catalog_path = catalog_path(locale)
    print("Merging catalog for %s at %s" % (locale, target_catalog_path))
    with open(target_catalog_path, "r") as target_catalog_file:
        catalog = read_po(target_catalog_file)
    if not default:
        with open(catalog_path(locale, "old.po"), "r") as target_catalog_file:
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
    source_catalog_path = catalog_path(default_locale, "messages.pot")
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
    print("Cleaning up")
    # Remove temp files for non-default locales
    for locale in supported_locales:
        if locale != default_locale:
            remove(catalog_path(locale, "old.po"))

    # Update template file for default locale
    with open(catalog_path(default_locale)) as catalog_file:
        catalog = read_po(catalog_file)
    for message in catalog:
        message.auto_comments.append("default-message: " + message.string)
        message.string = ""
    with open(
        catalog_path(default_locale, "messages.pot"), "wb"
    ) as source_catalog_file:
        write_po(
            source_catalog_file,
            catalog,
            ignore_obsolete=True,
            width=10000000,
            omit_header=True,
        )


def main(mode):
    if mode == "prepare":
        prepare()
    else:
        merge()
        clean()


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "merge"
    main(mode)
