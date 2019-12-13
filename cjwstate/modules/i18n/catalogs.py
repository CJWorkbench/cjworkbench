from cjworkbench.i18n import supported_locales, default_locale
from cjworkbench.i18n.catalogs.util import (
    read_po_catalog,
    write_po_catalog,
    remove_strings,
    find_fuzzy_messages,
    fill_catalog,
    mark_fuzzy,
    MessageUID,
    catalogs_are_same,
)
from babel.messages.catalog import Catalog
from cjwstate.modules.module_loader import ModuleFiles, ModuleSpec
from typing import FrozenSet, Dict
import pathlib
from cjwstate.modules.i18n.spec import find_spec_messages


def update_module_catalogs(directory: pathlib.Path):
    module_files = ModuleFiles.load_from_dirpath(directory)  # raise ValueError
    source_catalog = _build_source_catalog(ModuleSpec.load_from_path(module_files.spec))

    po_path = _po_path(directory, default_locale)

    try:
        old_source_catalog = read_po_catalog(po_path)
    except FileNotFoundError:
        old_source_catalog = Catalog(default_locale)

    if not catalogs_are_same(source_catalog, old_source_catalog):
        write_po_catalog(po_path, source_catalog)

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


def _build_source_catalog(spec: ModuleSpec) -> Catalog:
    messages = find_spec_messages(spec)
    # TODO: also find messages in module code
    source_catalog = Catalog(default_locale)
    for message_id, source_string in messages.items():
        source_catalog.add(message_id, string=source_string)

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
