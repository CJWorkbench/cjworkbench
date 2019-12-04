import logging
import os.path
import pathlib
import shutil
import tempfile
import time
from django.core.management.base import BaseCommand
from cjwstate.modules.module_loader import ModuleFiles, ModuleSpec
import cjwstate.modules
from cjworkbench.i18n import supported_locales, default_locale
from cjworkbench.i18n.catalogs.util import (
    read_po_catalog,
    write_po_catalog,
    remove_strings,
    find_fuzzy_messages,
    fill_catalog,
    mark_fuzzy,
)
from babel.messages.catalog import Catalog


logger = logging.getLogger(__name__)


def _po_path(basepath: os.path, locale_id: str, module_id_name: str) -> os.path:
    return os.path.join(basepath, "locale", locale_id, f"{module_id_name}.po")


def _find_param_messages(param, param_prefix):
    messages = {}
    messages[f"{param_prefix}.name"] = param.get("name")
    messages[f"{param_prefix}.placeholder"] = param.get("placeholder")
    if param["type"] == "string":
        messages[f"{param_prefix}.default"] = param.get("default")
    if param["type"] in ["menu", "radio"]:
        for option in param["options"]:
            if option != "separator":
                messages[f"{param_prefix}.options.{option.value}.label"] = option.get(
                    "label"
                )
    if param["type"] == "secret" and param["secret_logic"]["provider"] == "string":
        messages[f"{param_prefix}.secret_logic.label"] = param["secret_logic"].get(
            "label"
        )
        messages[f"{param_prefix}.secret_logic.placeholder"] = param[
            "secret_logic"
        ].get("placeholder")
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


def _build_source_catalog(spec: ModuleSpec) -> Catalog:
    prefix = f"modules.{spec.id_name}._spec"
    messages = {
        f"{prefix}.name": spec.get("name"),
        f"{prefix}.description": spec.get("description"),
        f"{prefix}.row_action_menu_entry_title": spec.get(
            "row_action_menu_entry_title"
        ),
        f"{prefix}.deprecated.message": spec.get("deprecated", {}).get("message"),
    }
    for param in spec.parameters:
        messages = {
            **_find_param_messages(param, f"{prefix}.parameters.{param['id_name']}"),
            **messages,
        }

    source_catalog = Catalog(default_locale)
    for message_id, source_string in messages.items():
        if source_string is not None:
            source_catalog.add(message_id, string=source_string)

    return source_catalog


def main(directory):
    cjwstate.modules.init_module_system()

    logger.info(f"Extracting...")

    with tempfile.TemporaryDirectory() as tmpdir:
        importdir = os.path.join(tmpdir, "importme")
        shutil.copytree(directory, importdir)
        shutil.rmtree(os.path.join(importdir, ".git"), ignore_errors=True)
        shutil.rmtree(os.path.join(importdir, ".eggs"), ignore_errors=True)
        shutil.rmtree(os.path.join(importdir, "node_modules"), ignore_errors=True)

        module_files = ModuleFiles.load_from_dirpath(
            pathlib.Path(importdir)
        )  # raise ValueError
        spec = ModuleSpec.load_from_path(module_files.spec)  # raise ValueError

    source_catalog = _build_source_catalog(spec)
    po_path = _po_path(directory, default_locale, spec.id_name)
    try:
        old_source_catalog = read_po_catalog(po_path)
    except FileNotFoundError:
        old_source_catalog = Catalog(default_locale)
    fuzzy = find_fuzzy_messages(
        old_catalog=old_source_catalog, new_catalog=source_catalog
    )
    write_po_catalog(po_path, source_catalog)
    logger.info(f"Found {len(fuzzy)} new fuzzy messages")

    for locale_id in supported_locales:
        po_path = _po_path(directory, locale_id, spec.id_name)
        try:
            old_catalog = read_po_catalog(po_path)
        except FileNotFoundError:
            old_catalog = Catalog(locale_id)
        catalog = Catalog(locale_id)
        fill_catalog(catalog, source_catalog, old_catalog)
        mark_fuzzy(catalog, fuzzy, old_catalog)
        write_po_catalog(po_path, catalog)


class Command(BaseCommand):
    help = "Find the internationalized texts of a module and export them to po files."

    def add_arguments(self, parser):
        parser.add_argument("directory")

    def handle(self, *args, **options):
        main(options["directory"])
