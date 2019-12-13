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
from typing import FrozenSet, Dict
import pathlib
from cjwstate.models.param_spec import ParamSpec, MenuOptionEnum
from functools import singledispatch


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
        "_spec.name": spec.get("name") or None,
        "_spec.description": spec.get("description") or None,
        "_spec.row_action_menu_entry_title": spec.get("row_action_menu_entry_title")
        or None,
        "_spec.deprecated.message": spec.get("deprecated", {}).get("message") or None,
    }
    for param_dict in spec.parameters:
        param_spec = ParamSpec.from_dict(param_dict)
        messages.update(
            extract_param_messages(param_spec, f"_spec.parameters.{param_spec.id_name}")
        )
    return messages


@singledispatch
def extract_param_messages(spec: ParamSpec, prefix: str) -> Dict[str, str]:
    return {}


def _add_if_set(
    messages: Dict[str, str], spec: object, prefix: str, key: str
) -> Dict[str, str]:
    value = getattr(spec, key)
    if value:
        messages.update({f"{prefix}.{key}": value})


@extract_param_messages.register(ParamSpec.String)
def _(spec: ParamSpec.String, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    _add_if_set(result, spec, prefix, "placeholder")
    _add_if_set(result, spec, prefix, "default")
    return result


@extract_param_messages.register(ParamSpec.Statictext)
def _(spec: ParamSpec.Statictext, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    return result


@extract_param_messages.register(ParamSpec.Integer)
def _(spec: ParamSpec.Integer, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    _add_if_set(result, spec, prefix, "placeholder")
    return result


@extract_param_messages.register(ParamSpec.Float)
def _(spec: ParamSpec.Float, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    _add_if_set(result, spec, prefix, "placeholder")
    return result


@extract_param_messages.register(ParamSpec.Checkbox)
def _(spec: ParamSpec.Checkbox, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    return result


@extract_param_messages.register(ParamSpec.Menu)
def _(spec: ParamSpec.Menu, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    _add_if_set(result, spec, prefix, "placeholder")
    for option in spec.options:
        if isinstance(option, MenuOptionEnum):
            _add_if_set(result, option, f"{prefix}.options.{option.value}", "label")
    return result


@extract_param_messages.register(ParamSpec.Radio)
def _(spec: ParamSpec.Radio, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    for option in spec.options:
        _add_if_set(result, option, f"{prefix}.options.{option.value}", "label")
    return result


@extract_param_messages.register(ParamSpec.Button)
def _(spec: ParamSpec.Button, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    return result


@extract_param_messages.register(ParamSpec.NumberFormat)
def _(spec: ParamSpec.NumberFormat, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    _add_if_set(result, spec, prefix, "placeholder")
    return result


@extract_param_messages.register(ParamSpec.Column)
def _(spec: ParamSpec.Column, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    _add_if_set(result, spec, prefix, "placeholder")
    return result


@extract_param_messages.register(ParamSpec.Multicolumn)
def _(spec: ParamSpec.Multicolumn, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    _add_if_set(result, spec, prefix, "placeholder")
    return result


@extract_param_messages.register(ParamSpec.Tab)
def _(spec: ParamSpec.Tab, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    _add_if_set(result, spec, prefix, "placeholder")
    return result


@extract_param_messages.register(ParamSpec.Multitab)
def _(spec: ParamSpec.Multitab, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    _add_if_set(result, spec, prefix, "placeholder")
    return result


@extract_param_messages.register(ParamSpec.Multichartseries)
def _(spec: ParamSpec.Multichartseries, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    return result


@extract_param_messages.register(ParamSpec.Secret)
def _(spec: ParamSpec.Secret, prefix: str) -> Dict[str, str]:
    result = {}
    if spec.secret_logic.provider == "string":
        secret_prefix = f"{prefix}.secret_logic"
        _add_if_set(result, spec.secret_logic, secret_prefix, "label")
        _add_if_set(result, spec.secret_logic, secret_prefix, "help")
        _add_if_set(result, spec.secret_logic, secret_prefix, "help_url")
        _add_if_set(result, spec.secret_logic, secret_prefix, "help_url_prompt")
    return result


@extract_param_messages.register(ParamSpec.Custom)
def _(spec: ParamSpec.Custom, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    return result


@extract_param_messages.register(ParamSpec.List)
def _(spec: ParamSpec.List, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    for child_spec in spec.child_parameters:
        result.update(
            extract_param_messages(
                child_spec, f"{prefix}.child_parameters.{child_spec.id_name}"
            )
        )
    return result
