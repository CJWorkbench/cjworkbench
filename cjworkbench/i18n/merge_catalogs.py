from babel.messages.pofile import read_po, write_po
from cjworkbench.i18n import default_locale, supported_locales, catalog_path
import re

_default_message_re = re.compile(r"\s*default-message:\s*(.*)\s*")


def _merge_catalog(locale, source_catalog, default={}):
    target_catalog_path = catalog_path(locale)
    print("Merging catalog for %s at %s" % (locale, target_catalog_path))
    catalog = read_po(open(target_catalog_path, "r"))
    for message in source_catalog:
        if message.id:  # ignore header
            catalog.__setitem__(message.id, message)
            if default and message.id in default:
                catalog[message.id].string = default[message.id]
    write_po(open(target_catalog_path, "wb"), catalog)


def main():
    source_catalog_path = catalog_path(default_locale, "messages.pot")
    source_catalog = read_po(open(source_catalog_path))
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


if __name__ == "__main__":
    main()
