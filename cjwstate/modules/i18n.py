from cjworkbench.i18n import supported_locales, default_locale
from cjworkbench.i18n.catalogs.util import (
    read_po_catalog,
    write_po_catalog,
    remove_strings,
    find_fuzzy_messages,
    fill_catalog,
    mark_fuzzy,
    MessageUID,
)
from babel.messages.catalog import Catalog
from cjwstate.modules.module_loader import ModuleFiles, ModuleSpec
from typing import FrozenSet
import pathlib


def update_module_catalogs(directory: pathlib.Path):
    module_files = ModuleFiles.load_from_dirpath(directory)  # raise ValueError
    source_catalog = _build_source_catalog(ModuleSpec.load_from_path(module_files.spec))

    po_path = _po_path(directory, default_locale)
    try:
        old_source_catalog = read_po_catalog(po_path)
    except FileNotFoundError:
        old_source_catalog = Catalog(default_locale)
    fuzzy = find_fuzzy_messages(
        old_catalog=old_source_catalog, new_catalog=source_catalog
    )
    write_po_catalog(po_path, source_catalog)

    for locale_id in supported_locales:
        po_path = _po_path(directory, locale_id)
        try:
            old_catalog = read_po_catalog(po_path)
        except FileNotFoundError:
            old_catalog = Catalog(locale_id)
        write_po_catalog(
            po_path,
            _merge_nonsource_catalog(locale_id, old_catalog, source_catalog, fuzzy),
        )


def _po_path(basepath: pathlib.Path, locale_id: str) -> pathlib.Path:
    return basepath / "locale" / locale_id / "messages.po"


def _build_source_catalog(spec: ModuleSpec) -> Catalog:
    messages = _find_spec_messages(spec)
    # TODO: also find messages in module code
    source_catalog = Catalog(default_locale)
    for message_id, source_string in messages.items():
        if source_string is not None:
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


def _find_spec_messages(spec: ModuleSpec) -> Catalog:
    messages = {
        "_spec.name": spec.get("name"),
        "_spec.description": spec.get("description"),
        "_spec.row_action_menu_entry_title": spec.get("row_action_menu_entry_title"),
        "_spec.deprecated.message": spec.get("deprecated", {}).get("message"),
    }
    for param in spec.parameters:
        messages = {
            **_find_param_messages(param, f"_spec.parameters.{param['id_name']}"),
            **messages,
        }
    return messages


def _find_param_messages(param, param_prefix):
    messages = {}
    messages[f"{param_prefix}.name"] = param.get("name")
    messages[f"{param_prefix}.placeholder"] = param.get("placeholder")
    if param["type"] == "string":
        messages[f"{param_prefix}.default"] = param.get("default")
    if param["type"] in ["menu", "radio"]:
        for option in param["options"]:
            if option != "separator":
                messages[
                    f"{param_prefix}.options.{option.get('value')}.label"
                ] = option.get("label")
    if param["type"] == "secret" and param["secret_logic"]["provider"] == "string":
        messages[f"{param_prefix}.secret_logic.label"] = param["secret_logic"].get(
            "label"
        )
        messages[f"{param_prefix}.secret_logic.help"] = param["secret_logic"].get(
            "help"
        )
        messages[f"{param_prefix}.secret_logic.help_url_prompt"] = param[
            "secret_logic"
        ].get("help_url_prompt")
        messages[f"{param_prefix}.secret_logic.help_url"] = param["secret_logic"].get(
            "help_url"
        )
    if param["type"] == "list":
        for child_param in param["child_parameters"]:
            messages = {
                **_find_param_messages(
                    child_param,
                    f"{param_prefix}.child_parameters.{child_param['id_name']}",
                ),
                **messages,
            }
    return messages
