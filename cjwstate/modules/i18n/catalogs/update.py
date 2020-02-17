import pathlib
from typing import FrozenSet
import zipfile
from babel.messages.catalog import Catalog
from cjworkbench.i18n import supported_locales, default_locale
from cjworkbench.i18n.catalogs.util import (
    read_po_catalog,
    write_po_catalog,
    find_fuzzy_messages,
    fill_catalog,
    mark_fuzzy,
    MessageUID,
    catalogs_are_same,
    move_strings_to_comments,
    copy_catalog,
)
from cjwstate.modules.types import ModuleZipfile
from cjwstate.importmodule import directory_loaded_as_zipfile_path
from cjwstate.modules.i18n.catalogs.extract.spec import find_spec_messages
from cjwstate.modules.i18n.catalogs.extract.code import find_messages_in_module_code


def extract_module_messages(directory: pathlib.Path):
    with directory_loaded_as_zipfile_path(directory) as zip_path:
        module_zipfile = ModuleZipfile(zip_path)  # may be invalid
        source_catalog = _build_source_catalog(module_zipfile)

    po_path = _po_path(directory, default_locale)

    try:
        old_source_catalog = read_po_catalog(po_path)
    except FileNotFoundError:
        old_source_catalog = Catalog(default_locale)

    # Update file for default locale
    if not catalogs_are_same(source_catalog, old_source_catalog):
        write_po_catalog(po_path, source_catalog)

    # Update template catalog
    # We will have no specific locale in the template catalog
    template_catalog = copy_catalog(source_catalog, locale=None)
    move_strings_to_comments(template_catalog, comment_tag="default-message")
    pot_path = _pot_path(directory)
    try:
        old_template_catalog = read_po_catalog(pot_path)
    except FileNotFoundError:
        old_template_catalog = Catalog()
    if not catalogs_are_same(template_catalog, old_template_catalog):
        write_po_catalog(
            pot_path,
            template_catalog,
            ignore_obsolete=True,
            width=10000000,  # we set a huge value for width, so that special comments do not wrap
            omit_header=True,  # removes locale and other info from the output file
        )

    fuzzy = find_fuzzy_messages(
        old_catalog=old_source_catalog, new_catalog=source_catalog
    )

    for locale_id in supported_locales:
        if locale_id != default_locale:
            po_path = _po_path(directory, locale_id)
            try:
                old_catalog = read_po_catalog(po_path)
            except FileNotFoundError:
                old_catalog = Catalog(locale_id)
            catalog = _merge_nonsource_catalog(
                locale_id, old_catalog, source_catalog, fuzzy
            )

            if not catalogs_are_same(catalog, old_catalog):
                write_po_catalog(po_path, catalog)


def _po_path(basepath: pathlib.Path, locale_id: str) -> pathlib.Path:
    return basepath / "locale" / locale_id / "messages.po"


def _pot_path(basepath: pathlib.Path) -> pathlib.Path:
    return basepath / "locale" / "templates" / "messages.pot"


def _build_source_catalog(module_zipfile: ModuleZipfile) -> Catalog:
    source_catalog = Catalog(default_locale)
    spec = module_zipfile.get_spec()
    for message_id, source_string in find_spec_messages(spec).items():
        source_catalog.add(message_id, string=source_string)
    with zipfile.ZipFile(module_zipfile.path, mode="r") as zf:
        for info in zf.infolist():
            if info.filename.endswith(".py"):
                with zf.open(info) as code_io:
                    for message_id, message_properties in find_messages_in_module_code(
                        code_io, info.filename
                    ).items():
                        source_catalog.add(
                            message_id,
                            string=message_properties["string"],
                            auto_comments=message_properties["comments"],
                            locations=message_properties["locations"],
                        )
    return source_catalog


def _merge_nonsource_catalog(
    locale_id: str,
    old_catalog: Catalog,
    source_catalog: Catalog,
    fuzzy: FrozenSet[MessageUID],
) -> Catalog:
    catalog = Catalog(locale_id)
    fill_catalog(catalog, source_catalog, old_catalog)
    mark_fuzzy(catalog, fuzzy, old_catalog)
    return catalog
