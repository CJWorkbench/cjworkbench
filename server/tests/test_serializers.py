import unittest
import logging
from io import BytesIO
from typing import Dict, List, Tuple

from cjwmodule.spec.loader import load_spec
from babel.messages.catalog import Catalog
from babel.messages.pofile import write_po

from cjwkernel.i18n import TODO_i18n
from cjwkernel.types import I18nMessage
from cjworkbench.tests.i18n.util import mock_app_catalogs, mock_cjwmodule_catalogs
from cjwstate.tests.utils import DbTestCaseWithModuleRegistry, create_module_zipfile
from cjwstate.clientside import ChartBlock, Module, Update, TableBlock, TextBlock
from server.serializers import (
    jsonize_i18n_message,
    JsonizeContext,
    JsonizeModuleContext,
    jsonize_clientside_module,
    jsonize_clientside_update,
)


def create_module_zipfile_with_catalogs(
    module_id_name: str, catalogs: Dict[str, Catalog]
):
    extra_file_contents = {}
    for catalog_locale_id, catalog in catalogs.items():
        po = BytesIO()
        write_po(po, catalog)
        extra_file_contents[f"locale/{catalog_locale_id}/messages.po"] = po.getvalue()
    return create_module_zipfile(
        module_id_name, extra_file_contents=extra_file_contents
    )


def mock_jsonize_context(
    user=None,
    user_profile=None,
    locale_id=None,
    module_catalogs_data: List[Tuple[str, Dict[str, Catalog]]] = [],
):
    module_zipfiles = {}
    if module_catalogs_data:
        for module_id_name, catalogs in module_catalogs_data:
            module_zipfiles[module_id_name] = create_module_zipfile_with_catalogs(
                module_id_name, catalogs
            )
    return JsonizeContext(
        user=user,
        user_profile=user_profile,
        locale_id=locale_id,
        module_zipfiles=module_zipfiles,
    )


DEFAULT_SERIALIZED_MODULE = {
    "id_name": None,
    "name": None,
    "category": None,
    "description": "",
    "deprecated": None,
    "icon": "url",
    "loads_data": False,
    "uses_data": True,
    "help_url": "",
    "has_zen_mode": False,
    "has_html_output": False,
    "row_action_menu_entry_title": "",
    "js_module": "",
    "param_fields": [],
}

DEFAULT_SERIALIZED_MODULE_PARAM = {"idName": None, "type": None, "visibleIf": None}


class JsonizeClientsideModuleTest(DbTestCaseWithModuleRegistry):
    def test_with_js(self):
        module = Module(
            load_spec(
                dict(
                    id_name="testme",
                    name="Test Module",
                    category="Clean",
                    parameters=[],
                )
            ),
            "var js = 1; console.log(js)",
        )
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(locale_id="el", module_catalogs_data=[("testme", {})]),
        )
        expected = {
            **DEFAULT_SERIALIZED_MODULE,
            "id_name": "testme",
            "name": "Test Module",
            "category": "Clean",
            "js_module": "var js = 1; console.log(js)",
        }
        self.assertDictEqual(result, expected)

    def test_no_params_translate(self):
        module = Module(
            load_spec(
                dict(
                    id_name="testme",
                    name="Test Module",
                    category="Clean",
                    parameters=[],
                )
            ),
            "",
        )
        catalog = Catalog()
        catalog.add("_spec.name", string="Translated name")
        default_catalog = Catalog()
        default_catalog.add("_spec.name", string="Default translated name")
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                module_catalogs_data=[
                    ("testme", {"el": catalog, "en": default_catalog})
                ],
            ),
        )
        expected = {
            **DEFAULT_SERIALIZED_MODULE,
            "id_name": "testme",
            "name": "Translated name",
            "category": "Clean",
        }
        self.assertDictEqual(result, expected)

    def test_no_params_translate_message_empty_in_catalog_but_exists_in_default_catalog(
        self,
    ):
        module = Module(
            load_spec(
                dict(
                    id_name="testme",
                    name="Test Module",
                    category="Clean",
                    parameters=[],
                )
            ),
            "",
        )
        catalog = Catalog()
        catalog.add("_spec.name", string="")
        default_catalog = Catalog()
        default_catalog.add("_spec.name", string="Default translated name")
        # The following should NOT produce a log entry
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                module_catalogs_data=[
                    ("testme", {"el": catalog, "en": default_catalog})
                ],
            ),
        )
        expected = {
            **DEFAULT_SERIALIZED_MODULE,
            "id_name": "testme",
            "name": "Default translated name",
            "category": "Clean",
        }
        self.assertDictEqual(result, expected)

    def test_no_params_translate_message_only_exists_in_default_catalog(self):
        module = Module(
            load_spec(
                dict(
                    id_name="testme",
                    name="Test Module",
                    category="Clean",
                    parameters=[],
                )
            ),
            "",
        )
        catalog = Catalog()
        default_catalog = Catalog()
        default_catalog.add("_spec.name", string="Default translated name")
        # The following should NOT produce a log entry
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                module_catalogs_data=[
                    ("testme", {"el": catalog, "en": default_catalog})
                ],
            ),
        )
        expected = {
            **DEFAULT_SERIALIZED_MODULE,
            "id_name": "testme",
            "name": "Default translated name",
            "category": "Clean",
        }
        self.assertDictEqual(result, expected)

    def test_no_params_translate_message_empty_in_all_catalogs(self):
        module = Module(
            load_spec(
                dict(
                    id_name="testme",
                    name="Test Module",
                    category="Clean",
                    parameters=[],
                )
            ),
            "",
        )
        catalog = Catalog()
        catalog.add("_spec.name", string="")
        default_catalog = Catalog()
        default_catalog.add("_spec.name", string="")
        with self.assertLogs(level=logging.ERROR):
            result = jsonize_clientside_module(
                module,
                mock_jsonize_context(
                    locale_id="el",
                    module_catalogs_data=[
                        ("testme", {"el": catalog, "en": default_catalog})
                    ],
                ),
            )
        expected = {
            **DEFAULT_SERIALIZED_MODULE,
            "id_name": "testme",
            "name": "Test Module",
            "category": "Clean",
        }
        self.assertDictEqual(result, expected)

    def test_no_params_translate_empty_catalogs(self):
        module = Module(
            load_spec(
                dict(
                    id_name="testme",
                    name="Test Module",
                    category="Clean",
                    parameters=[],
                )
            ),
            "",
        )
        catalog = Catalog()
        default_catalog = Catalog()
        with self.assertLogs(level=logging.ERROR):
            result = jsonize_clientside_module(
                module,
                mock_jsonize_context(
                    locale_id="el",
                    module_catalogs_data=[
                        ("testme", {"el": catalog, "en": default_catalog})
                    ],
                ),
            )
        expected = {
            **DEFAULT_SERIALIZED_MODULE,
            "id_name": "testme",
            "name": "Test Module",
            "category": "Clean",
        }
        self.assertDictEqual(result, expected)

    def test_no_params_translate_not_internationalized(self):
        module = Module(
            load_spec(
                dict(
                    id_name="testme",
                    name="Test Module",
                    category="Clean",
                    parameters=[],
                )
            ),
            "",
        )
        # The following should NOT produce a log entry
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(locale_id="el", module_catalogs_data=[("testme", {})]),
        )
        expected = {
            **DEFAULT_SERIALIZED_MODULE,
            "id_name": "testme",
            "name": "Test Module",
            "category": "Clean",
        }
        self.assertDictEqual(result, expected)

    def test_no_params_translate_not_in_context(self):
        module = Module(
            load_spec(
                dict(
                    id_name="testme",
                    name="Test Module",
                    category="Clean",
                    parameters=[],
                )
            ),
            "",
        )
        with self.assertLogs(level=logging.ERROR):
            result = jsonize_clientside_module(
                module, mock_jsonize_context(locale_id="el", module_catalogs_data=[])
            )
        expected = {
            **DEFAULT_SERIALIZED_MODULE,
            "id_name": "testme",
            "name": "Test Module",
            "category": "Clean",
        }
        self.assertDictEqual(result, expected)

    # Tests that translatable catalog entries which are not in the spec are ignored
    def test_no_params_translate_superfluous_catalog(self):
        module = Module(
            load_spec(
                dict(
                    id_name="testme",
                    name="Test Module",
                    category="Clean",
                    parameters=[],
                )
            ),
            "",
        )
        catalog = Catalog()
        default_catalog = Catalog()
        default_catalog.add("_spec.name", string="Test Module")
        default_catalog.add("_spec.row_action_menu_entry_title", string="Title")
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                module_catalogs_data=[
                    ("testme", {"el": catalog, "en": default_catalog})
                ],
            ),
        )
        expected = {
            **DEFAULT_SERIALIZED_MODULE,
            "id_name": "testme",
            "name": "Test Module",
            "category": "Clean",
        }
        self.assertDictEqual(result, expected)

    def test_everything_except_parameters(self):
        module = Module(
            load_spec(
                dict(
                    id_name="testme",
                    name="Test Module",
                    category="Clean",
                    parameters=[],
                    description="I do that",
                    deprecated={
                        "message": "Please use something else",
                        "end_date": "2030-12-31",
                    },
                    icon="url",
                    link="http://example.com/module",
                    loads_data=False,
                    uses_data=True,
                    html_output=False,
                    has_zen_mode=True,
                    row_action_menu_entry_title="Solve your problem",
                    help_url="testme",
                )
            ),
            "",
        )
        catalog = Catalog()
        catalog.add("_spec.name", string="Name translated")
        catalog.add("_spec.description", string="Description translated")
        default_catalog = Catalog()
        default_catalog.add("_spec.name", string="Name default")
        default_catalog.add("_spec.description", string="Description default")
        default_catalog.add("_spec.deprecated.message", string="Deprecated default")
        default_catalog.add(
            "_spec.row_action_menu_entry_title", string="Action default"
        )
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                module_catalogs_data=[
                    ("testme", {"el": catalog, "en": default_catalog})
                ],
            ),
        )
        expected = {
            **DEFAULT_SERIALIZED_MODULE,
            "id_name": "testme",
            "name": "Name translated",
            "category": "Clean",
            "param_fields": [],
            "description": "Description translated",
            "deprecated": {"message": "Deprecated default", "end_date": "2030-12-31"},
            "icon": "url",
            "loads_data": False,
            "uses_data": True,
            "has_html_output": False,
            "has_zen_mode": True,
            "row_action_menu_entry_title": "Action default",
            "help_url": "http://help.workbenchdata.com/testme",
        }
        self.assertDictEqual(result, expected)

    def test_everything_with_parameters(self):
        module = Module(
            load_spec(
                dict(
                    id_name="testme",
                    name="Test Module",
                    category="Clean",
                    parameters=[
                        {
                            "id_name": "hello",
                            "type": "list",
                            "name": "Hello there!",
                            "child_parameters": [
                                {
                                    "id_name": "hello2",
                                    "type": "statictext",
                                    "name": "Hello there 2!",
                                }
                            ],
                        }
                    ],
                    description="I do that",
                    deprecated={
                        "message": "Please use something else",
                        "end_date": "2030-12-31",
                    },
                    icon="url",
                    link="http://example.com/module",
                    loads_data=False,
                    uses_data=True,
                    html_output=False,
                    has_zen_mode=True,
                    row_action_menu_entry_title="Solve your problem",
                    help_url="testme",
                )
            ),
            "",
        )
        catalog = Catalog()
        catalog.add("_spec.name", string="Name translated")
        catalog.add("_spec.description", string="Description translated")
        catalog.add("_spec.parameters.hello.name", string="Hello translated")
        default_catalog = Catalog()
        default_catalog.add("_spec.name", string="Name default")
        default_catalog.add("_spec.description", string="Description default")
        default_catalog.add("_spec.deprecated.message", string="Deprecated default")
        default_catalog.add(
            "_spec.row_action_menu_entry_title", string="Action default"
        )
        default_catalog.add("_spec.parameters.hello.name", string="Hello default")
        default_catalog.add(
            "_spec.parameters.hello.child_parameters.hello2.name",
            string="Hello2 default",
        )
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                module_catalogs_data=[
                    ("testme", {"el": catalog, "en": default_catalog})
                ],
            ),
        )
        expected = {
            **DEFAULT_SERIALIZED_MODULE,
            "id_name": "testme",
            "name": "Name translated",
            "category": "Clean",
            "param_fields": [
                {
                    **DEFAULT_SERIALIZED_MODULE_PARAM,
                    "idName": "hello",
                    "type": "list",
                    "name": "Hello translated",
                    "childDefault": {},
                    "childParameters": [
                        {
                            **DEFAULT_SERIALIZED_MODULE_PARAM,
                            "idName": "hello2",
                            "type": "statictext",
                            "name": "Hello2 default",
                        }
                    ],
                }
            ],
            "description": "Description translated",
            "deprecated": {"message": "Deprecated default", "end_date": "2030-12-31"},
            "icon": "url",
            "loads_data": False,
            "uses_data": True,
            "has_html_output": False,
            "has_zen_mode": True,
            "row_action_menu_entry_title": "Action default",
            "help_url": "http://help.workbenchdata.com/testme",
        }
        self.assertDictEqual(result, expected)

    def test_parameter_type_statictext(self):
        module = Module(
            load_spec(
                dict(
                    id_name="testme",
                    name="Test Module",
                    category="Clean",
                    parameters=[
                        {
                            "id_name": "hello",
                            "type": "statictext",
                            "name": "Hello there!",
                        }
                    ],
                )
            ),
            "",
        )
        catalog = Catalog()
        catalog.add("_spec.parameters.hello.name", string="Hello translated")
        default_catalog = Catalog()
        default_catalog.add("_spec.name", string="Test Module")
        default_catalog.add("_spec.parameters.hello.name", string="Hello default")
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                module_catalogs_data=[
                    ("testme", {"el": catalog, "en": default_catalog})
                ],
            ),
        )
        expected = [
            {
                **DEFAULT_SERIALIZED_MODULE_PARAM,
                "idName": "hello",
                "type": "statictext",
                "name": "Hello translated",
            }
        ]
        self.assertEqual(result["param_fields"], expected)

    def test_parameter_type_string(self):
        module = Module(
            load_spec(
                dict(
                    id_name="testme",
                    name="Test Module",
                    category="Clean",
                    parameters=[
                        {
                            "id_name": "hello",
                            "type": "string",
                            "name": "Hello there!",
                            "placeholder": "Hey",
                            "multiline": False,
                            "default": "H",
                        }
                    ],
                )
            ),
            "",
        )
        catalog = Catalog()
        catalog.add("_spec.parameters.hello.name", string="Hello translated")
        default_catalog = Catalog()
        default_catalog.add("_spec.name", string="Test Module")
        default_catalog.add("_spec.parameters.hello.name", string="Hello default")
        default_catalog.add("_spec.parameters.hello.placeholder", string="Fill me")
        default_catalog.add("_spec.parameters.hello.default", string="Default")
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                module_catalogs_data=[
                    ("testme", {"el": catalog, "en": default_catalog})
                ],
            ),
        )
        expected = [
            {
                **DEFAULT_SERIALIZED_MODULE_PARAM,
                "idName": "hello",
                "type": "string",
                "name": "Hello translated",
                "placeholder": "Fill me",
                "multiline": False,
                "syntax": None,
                "default": "Default",
            }
        ]
        self.assertEqual(result["param_fields"], expected)

    def test_parameter_type_integer(self):
        module = Module(
            load_spec(
                dict(
                    id_name="testme",
                    name="Test Module",
                    category="Clean",
                    parameters=[
                        {
                            "id_name": "hello",
                            "type": "integer",
                            "name": "Hello there!",
                            "placeholder": "Hey",
                            "default": 3,
                        }
                    ],
                )
            ),
            "",
        )
        catalog = Catalog()
        catalog.add("_spec.parameters.hello.name", string="Hello translated")
        default_catalog = Catalog()
        default_catalog.add("_spec.name", string="Test Module")
        default_catalog.add("_spec.parameters.hello.name", string="Hello default")
        default_catalog.add("_spec.parameters.hello.placeholder", string="Fill me")
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                module_catalogs_data=[
                    ("testme", {"el": catalog, "en": default_catalog})
                ],
            ),
        )
        expected = [
            {
                **DEFAULT_SERIALIZED_MODULE_PARAM,
                "idName": "hello",
                "type": "integer",
                "name": "Hello translated",
                "placeholder": "Fill me",
                "default": 3,
            }
        ]
        self.assertEqual(result["param_fields"], expected)

    def test_parameter_type_float(self):
        module = Module(
            load_spec(
                dict(
                    id_name="testme",
                    name="Test Module",
                    category="Clean",
                    parameters=[
                        {
                            "id_name": "hello",
                            "type": "float",
                            "name": "Hello there!",
                            "placeholder": "Hey",
                            "default": 3.4,
                        }
                    ],
                )
            ),
            "",
        )
        catalog = Catalog()
        catalog.add("_spec.parameters.hello.name", string="Hello translated")
        default_catalog = Catalog()
        default_catalog.add("_spec.name", string="Test Module")
        default_catalog.add("_spec.parameters.hello.name", string="Hello default")
        default_catalog.add("_spec.parameters.hello.placeholder", string="Fill me")
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                module_catalogs_data=[
                    ("testme", {"el": catalog, "en": default_catalog})
                ],
            ),
        )
        expected = [
            {
                **DEFAULT_SERIALIZED_MODULE_PARAM,
                "idName": "hello",
                "type": "float",
                "name": "Hello translated",
                "placeholder": "Fill me",
                "default": 3.4,
            }
        ]
        self.assertEqual(result["param_fields"], expected)

    def test_parameter_type_checkbox(self):
        module = Module(
            load_spec(
                dict(
                    id_name="testme",
                    name="Test Module",
                    category="Clean",
                    parameters=[
                        {
                            "id_name": "hello",
                            "type": "checkbox",
                            "name": "Hello there!",
                            "default": True,
                        }
                    ],
                )
            ),
            "",
        )
        catalog = Catalog()
        catalog.add("_spec.parameters.hello.name", string="Hello translated")
        default_catalog = Catalog()
        default_catalog.add("_spec.name", string="Test Module")
        default_catalog.add("_spec.parameters.hello.name", string="Hello default")
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                module_catalogs_data=[
                    ("testme", {"el": catalog, "en": default_catalog})
                ],
            ),
        )
        expected = [
            {
                **DEFAULT_SERIALIZED_MODULE_PARAM,
                "idName": "hello",
                "type": "checkbox",
                "name": "Hello translated",
                "default": True,
            }
        ]
        self.assertEqual(result["param_fields"], expected)

    def test_parameter_type_menu(self):
        module = Module(
            load_spec(
                dict(
                    id_name="testme",
                    name="Test Module",
                    category="Clean",
                    parameters=[
                        {
                            "id_name": "hello",
                            "type": "menu",
                            "name": "Hello there!",
                            "placeholder": "Choose something...",
                            "options": [
                                {"label": "First", "value": "first"},
                                "separator",
                                {"label": "Second", "value": "second"},
                            ],
                            "default": "first",
                        }
                    ],
                )
            ),
            "",
        )
        catalog = Catalog()
        catalog.add("_spec.parameters.hello.name", string="Hello translated")
        catalog.add(
            "_spec.parameters.hello.options.first.label", string="First translated"
        )
        default_catalog = Catalog()
        default_catalog.add("_spec.name", string="Test Module")
        default_catalog.add("_spec.parameters.hello.name", string="Hello default")
        default_catalog.add("_spec.parameters.hello.placeholder", string="Fill me")
        default_catalog.add(
            "_spec.parameters.hello.options.first.label", string="First default"
        )
        default_catalog.add(
            "_spec.parameters.hello.options.second.label", string="Second default"
        )
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                module_catalogs_data=[
                    ("testme", {"el": catalog, "en": default_catalog})
                ],
            ),
        )
        expected = [
            {
                **DEFAULT_SERIALIZED_MODULE_PARAM,
                "idName": "hello",
                "type": "menu",
                "name": "Hello translated",
                "placeholder": "Fill me",
                "options": [
                    {"label": "First translated", "value": "first"},
                    "separator",
                    {"label": "Second default", "value": "second"},
                ],
                "default": "first",
            }
        ]
        self.assertEqual(result["param_fields"], expected)

    def test_parameter_type_radio(self):
        module = Module(
            load_spec(
                dict(
                    id_name="testme",
                    name="Test Module",
                    category="Clean",
                    parameters=[
                        {
                            "id_name": "hello",
                            "type": "radio",
                            "name": "Hello there!",
                            "options": [
                                {"label": "First", "value": "first"},
                                {"label": "Second", "value": True},
                            ],
                            "default": "first",
                        }
                    ],
                )
            ),
            "",
        )
        catalog = Catalog()
        catalog.add("_spec.parameters.hello.name", string="Hello translated")
        catalog.add(
            "_spec.parameters.hello.options.first.label", string="First translated"
        )
        default_catalog = Catalog()
        default_catalog.add("_spec.name", string="Test Module")
        default_catalog.add("_spec.parameters.hello.name", string="Hello default")
        default_catalog.add(
            "_spec.parameters.hello.options.first.label", string="First default"
        )
        default_catalog.add(
            "_spec.parameters.hello.options.True.label", string="Second default"
        )
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                module_catalogs_data=[
                    ("testme", {"el": catalog, "en": default_catalog})
                ],
            ),
        )
        expected = [
            {
                **DEFAULT_SERIALIZED_MODULE_PARAM,
                "idName": "hello",
                "type": "radio",
                "name": "Hello translated",
                "options": [
                    {"label": "First translated", "value": "first"},
                    {"label": "Second default", "value": True},
                ],
                "default": "first",
            }
        ]
        self.assertEqual(result["param_fields"], expected)

    def test_parameter_type_numberformat(self):
        module = Module(
            load_spec(
                dict(
                    id_name="testme",
                    name="Test Module",
                    category="Clean",
                    parameters=[
                        {
                            "id_name": "hello",
                            "type": "numberformat",
                            "name": "Hello there!",
                        }
                    ],
                )
            ),
            "",
        )
        catalog = Catalog()
        catalog.add("_spec.parameters.hello.name", string="Hello translated")
        default_catalog = Catalog()
        default_catalog.add("_spec.name", string="Test Module")
        default_catalog.add("_spec.parameters.hello.name", string="Hello default")
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                module_catalogs_data=[
                    ("testme", {"el": catalog, "en": default_catalog})
                ],
            ),
        )
        expected = [
            {
                **DEFAULT_SERIALIZED_MODULE_PARAM,
                "idName": "hello",
                "type": "numberformat",
                "name": "Hello translated",
                "default": "{:,}",
            }
        ]
        self.assertEqual(result["param_fields"], expected)

    def test_parameter_type_column(self):
        module = Module(
            load_spec(
                dict(
                    id_name="testme",
                    name="Test Module",
                    category="Clean",
                    parameters=[
                        {
                            "id_name": "hello",
                            "type": "column",
                            "name": "Hello there!",
                            "placeholder": "Fill me",
                            "column_types": ["text"],
                            "tab_parameter": "tab",
                        },
                        {"id_name": "tab", "type": "tab", "name": "Hello there 2!"},
                    ],
                )
            ),
            "",
        )
        catalog = Catalog()
        catalog.add("_spec.parameters.hello.name", string="Hello translated")
        default_catalog = Catalog()
        default_catalog.add("_spec.name", string="Test Module")
        default_catalog.add("_spec.parameters.tab.name", string="Hello there 2!")
        default_catalog.add("_spec.parameters.hello.name", string="Hello default")
        default_catalog.add(
            "_spec.parameters.hello.placeholder", string="Fill me default"
        )
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                module_catalogs_data=[
                    ("testme", {"el": catalog, "en": default_catalog})
                ],
            ),
        )
        expected = [
            {
                **DEFAULT_SERIALIZED_MODULE_PARAM,
                "idName": "hello",
                "type": "column",
                "name": "Hello translated",
                "placeholder": "Fill me default",
                "columnTypes": ["text"],
                "tabParameter": "tab",
            },
            {
                **DEFAULT_SERIALIZED_MODULE_PARAM,
                "idName": "tab",
                "type": "tab",
                "name": "Hello there 2!",
                "placeholder": "",
            },
        ]
        self.assertEqual(result["param_fields"], expected)

    def test_parameter_type_multicolumn(self):
        module = Module(
            load_spec(
                dict(
                    id_name="testme",
                    name="Test Module",
                    category="Clean",
                    parameters=[
                        {
                            "id_name": "hello",
                            "type": "multicolumn",
                            "name": "Hello there!",
                            "placeholder": "Fill me",
                            "column_types": ["text"],
                            "tab_parameter": "tab",
                        },
                        {"id_name": "tab", "type": "tab", "name": "Hello there 2!"},
                    ],
                )
            ),
            "",
        )
        catalog = Catalog()
        catalog.add("_spec.parameters.hello.name", string="Hello translated")
        default_catalog = Catalog()
        default_catalog.add("_spec.name", string="Test Module")
        default_catalog.add("_spec.parameters.tab.name", string="Hello there 2!")
        default_catalog.add("_spec.parameters.hello.name", string="Hello default")
        default_catalog.add(
            "_spec.parameters.hello.placeholder", string="Fill me default"
        )
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                module_catalogs_data=[
                    ("testme", {"el": catalog, "en": default_catalog})
                ],
            ),
        )
        expected = [
            {
                **DEFAULT_SERIALIZED_MODULE_PARAM,
                "idName": "hello",
                "type": "multicolumn",
                "name": "Hello translated",
                "placeholder": "Fill me default",
                "columnTypes": ["text"],
                "tabParameter": "tab",
            },
            {
                **DEFAULT_SERIALIZED_MODULE_PARAM,
                "idName": "tab",
                "type": "tab",
                "name": "Hello there 2!",
                "placeholder": "",
            },
        ]
        self.assertEqual(result["param_fields"], expected)

    def test_parameter_type_tab(self):
        module = Module(
            load_spec(
                dict(
                    id_name="testme",
                    name="Test Module",
                    category="Clean",
                    parameters=[
                        {
                            "id_name": "hello",
                            "type": "tab",
                            "name": "Hello there!",
                            "placeholder": "Fill me",
                        }
                    ],
                )
            ),
            "",
        )
        catalog = Catalog()
        catalog.add("_spec.parameters.hello.name", string="Hello translated")
        default_catalog = Catalog()
        default_catalog.add("_spec.name", string="Test Module")
        default_catalog.add("_spec.parameters.hello.name", string="Hello default")
        default_catalog.add(
            "_spec.parameters.hello.placeholder", string="Fill me default"
        )
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                module_catalogs_data=[
                    ("testme", {"el": catalog, "en": default_catalog})
                ],
            ),
        )
        expected = [
            {
                **DEFAULT_SERIALIZED_MODULE_PARAM,
                "idName": "hello",
                "type": "tab",
                "name": "Hello translated",
                "placeholder": "Fill me default",
            }
        ]
        self.assertEqual(result["param_fields"], expected)

    def test_parameter_type_multitab(self):
        module = Module(
            load_spec(
                dict(
                    id_name="testme",
                    name="Test Module",
                    category="Clean",
                    parameters=[
                        {
                            "id_name": "hello",
                            "type": "multitab",
                            "name": "Hello there!",
                            "placeholder": "Fill me",
                        }
                    ],
                )
            ),
            "",
        )
        catalog = Catalog()
        catalog.add("_spec.parameters.hello.name", string="Hello translated")
        default_catalog = Catalog()
        default_catalog.add("_spec.name", string="Test Module")
        default_catalog.add("_spec.parameters.hello.name", string="Hello default")
        default_catalog.add(
            "_spec.parameters.hello.placeholder", string="Fill me default"
        )
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                module_catalogs_data=[
                    ("testme", {"el": catalog, "en": default_catalog})
                ],
            ),
        )
        expected = [
            {
                **DEFAULT_SERIALIZED_MODULE_PARAM,
                "idName": "hello",
                "type": "multitab",
                "name": "Hello translated",
                "placeholder": "Fill me default",
            }
        ]
        self.assertEqual(result["param_fields"], expected)

    def test_parameter_type_multichartseries(self):
        module = Module(
            load_spec(
                dict(
                    id_name="testme",
                    name="Test Module",
                    category="Clean",
                    parameters=[
                        {
                            "id_name": "hello",
                            "type": "multichartseries",
                            "name": "Hello there!",
                        }
                    ],
                )
            ),
            "",
        )
        catalog = Catalog()
        catalog.add("_spec.parameters.hello.name", string="Hello translated")
        default_catalog = Catalog()
        default_catalog.add("_spec.name", string="Test Module")
        default_catalog.add("_spec.parameters.hello.name", string="Hello default")
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                module_catalogs_data=[
                    ("testme", {"el": catalog, "en": default_catalog})
                ],
            ),
        )
        expected = [
            {
                **DEFAULT_SERIALIZED_MODULE_PARAM,
                "idName": "hello",
                "type": "multichartseries",
                "placeholder": "",
                "name": "Hello translated",
            }
        ]
        self.assertEqual(result["param_fields"], expected)

    def test_parameter_type_secret_string(self):
        module = Module(
            load_spec(
                dict(
                    id_name="testme",
                    name="Test Module",
                    category="Clean",
                    parameters=[
                        {
                            "id_name": "hello",
                            "type": "secret",
                            "secret_logic": {
                                "provider": "string",
                                "label": "Secret",
                                "pattern": "[A-Z]{10,12}",
                                "placeholder": "AAAAAAAAAAAA",
                                "help": "Find it there",
                                "help_url_prompt": "Take me there",
                                "help_url": "https://example.com/get_secret",
                            },
                        }
                    ],
                )
            ),
            "",
        )
        catalog = Catalog()
        catalog.add("_spec.parameters.hello.name", string="Hello translated")
        catalog.add(
            "_spec.parameters.hello.secret_logic.label", string="Label translated"
        )
        catalog.add(
            "_spec.parameters.hello.secret_logic.help", string="Help translated"
        )
        catalog.add(
            "_spec.parameters.hello.secret_logic.help_url_prompt",
            string="Help URL prompt translated",
        )
        default_catalog = Catalog()
        default_catalog.add("_spec.name", string="Test Module")
        default_catalog.add("_spec.parameters.hello.name", string="Hello default")
        default_catalog.add(
            "_spec.parameters.hello.secret_logic.label", string="Label default"
        )
        default_catalog.add(
            "_spec.parameters.hello.secret_logic.help", string="Help default"
        )
        default_catalog.add(
            "_spec.parameters.hello.secret_logic.help_url", string="Help URL default"
        )
        default_catalog.add(
            "_spec.parameters.hello.secret_logic.help_url_prompt",
            string="Help URL prompt default",
        )
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                module_catalogs_data=[
                    ("testme", {"el": catalog, "en": default_catalog})
                ],
            ),
        )
        expected = [
            {
                **DEFAULT_SERIALIZED_MODULE_PARAM,
                "idName": "hello",
                "type": "secret",
                "secretLogic": {
                    "provider": "string",
                    "label": "Label translated",
                    "pattern": "[A-Z]{10,12}",
                    "placeholder": "AAAAAAAAAAAA",
                    "help": "Help translated",
                    "helpUrlPrompt": "Help URL prompt translated",
                    "helpUrl": "Help URL default",
                },
            }
        ]
        self.assertEqual(result["param_fields"], expected)

    def test_parameter_type_secret_oauth2(self):
        module = Module(
            load_spec(
                dict(
                    id_name="googlesheets",
                    name="Test Module",
                    category="Clean",
                    parameters=[
                        {
                            "id_name": "hello",
                            "type": "secret",
                            "secret_logic": {"provider": "oauth2", "service": "google"},
                        }
                    ],
                )
            ),
            "",
        )
        catalog = Catalog()
        default_catalog = Catalog()
        default_catalog.add("_spec.name", string="Test Module")
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                module_catalogs_data=[
                    ("googlesheets", {"el": catalog, "en": default_catalog})
                ],
            ),
        )
        expected = [
            {
                **DEFAULT_SERIALIZED_MODULE_PARAM,
                "idName": "hello",
                "type": "secret",
                "secretLogic": {"provider": "oauth2", "service": "google"},
            }
        ]
        self.assertEqual(result["param_fields"], expected)

    def test_parameter_type_secret_oauth1a(self):
        module = Module(
            load_spec(
                dict(
                    id_name="twitter",
                    name="Test Module",
                    category="Clean",
                    parameters=[
                        {
                            "id_name": "hello",
                            "type": "secret",
                            "secret_logic": {
                                "provider": "oauth1a",
                                "service": "twitter",
                            },
                        }
                    ],
                )
            ),
            "",
        )
        catalog = Catalog()
        default_catalog = Catalog()
        default_catalog.add("_spec.name", string="Test Module")
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                module_catalogs_data=[
                    ("twitter", {"el": catalog, "en": default_catalog})
                ],
            ),
        )
        expected = [
            {
                **DEFAULT_SERIALIZED_MODULE_PARAM,
                "idName": "hello",
                "type": "secret",
                "secretLogic": {"provider": "oauth1a", "service": "twitter"},
            }
        ]
        self.assertEqual(result["param_fields"], expected)

    def test_parameter_type_gdrivefile(self):
        module = Module(
            load_spec(
                dict(
                    id_name="googlesheets",
                    name="Test Module",
                    category="Clean",
                    parameters=[
                        {
                            "id_name": "google",
                            "type": "secret",
                            "secret_logic": {"provider": "oauth2", "service": "google"},
                        },
                        {
                            "id_name": "hello2",
                            "type": "gdrivefile",
                            "secret_parameter": "google",
                        },
                    ],
                )
            ),
            "",
        )
        catalog = Catalog()
        default_catalog = Catalog()
        default_catalog.add("_spec.name", string="Test Module")
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                module_catalogs_data=[
                    ("googlesheets", {"el": catalog, "en": default_catalog})
                ],
            ),
        )
        expected = [
            {
                **DEFAULT_SERIALIZED_MODULE_PARAM,
                "idName": "google",
                "type": "secret",
                "secretLogic": {"provider": "oauth2", "service": "google"},
            },
            {
                **DEFAULT_SERIALIZED_MODULE_PARAM,
                "idName": "hello2",
                "type": "gdrivefile",
                "name": "",
                "secretParameter": "google",
            },
        ]
        self.assertEqual(result["param_fields"], expected)

    def test_parameter_type_file(self):
        module = Module(
            load_spec(
                dict(
                    id_name="testme",
                    name="Test Module",
                    category="Clean",
                    parameters=[{"id_name": "hello", "type": "file"}],
                )
            ),
            "",
        )
        catalog = Catalog()
        default_catalog = Catalog()
        default_catalog.add("_spec.name", string="Test Module")
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                module_catalogs_data=[
                    ("testme", {"el": catalog, "en": default_catalog})
                ],
            ),
        )
        expected = [
            {**DEFAULT_SERIALIZED_MODULE_PARAM, "idName": "hello", "type": "file"}
        ]
        self.assertEqual(result["param_fields"], expected)

    def test_parameter_type_custom(self):
        module = Module(
            load_spec(
                dict(
                    id_name="testme",
                    name="Test Module",
                    category="Clean",
                    parameters=[
                        {"id_name": "hello", "type": "custom", "name": "Hello there!"}
                    ],
                )
            ),
            "",
        )
        catalog = Catalog()
        catalog.add("_spec.parameters.hello.name", string="Hello translated")
        default_catalog = Catalog()
        default_catalog.add("_spec.name", string="Test Module")
        default_catalog.add("_spec.parameters.hello.name", string="Hello default")
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                module_catalogs_data=[
                    ("testme", {"el": catalog, "en": default_catalog})
                ],
            ),
        )
        expected = [
            {
                **DEFAULT_SERIALIZED_MODULE_PARAM,
                "idName": "hello",
                "type": "custom",
                "default": "",
                "name": "Hello translated",
            }
        ]
        self.assertEqual(result["param_fields"], expected)

    def test_parameter_type_list(self):
        module = Module(
            load_spec(
                dict(
                    id_name="testme",
                    name="Test Module",
                    category="Clean",
                    parameters=[
                        {
                            "id_name": "hello",
                            "type": "list",
                            "name": "Hello there!",
                            "child_parameters": [
                                {
                                    "id_name": "hello2",
                                    "type": "statictext",
                                    "name": "Hello there 2!",
                                }
                            ],
                        }
                    ],
                )
            ),
            "",
        )
        catalog = Catalog()
        catalog.add("_spec.parameters.hello.name", string="Hello translated")
        default_catalog = Catalog()
        default_catalog.add("_spec.name", string="Test Module")
        default_catalog.add("_spec.parameters.hello.name", string="Hello default")
        default_catalog.add(
            "_spec.parameters.hello.child_parameters.hello2.name",
            string="Hello2 default",
        )
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                module_catalogs_data=[
                    ("testme", {"el": catalog, "en": default_catalog})
                ],
            ),
        )
        expected = [
            {
                **DEFAULT_SERIALIZED_MODULE_PARAM,
                "idName": "hello",
                "type": "list",
                "name": "Hello translated",
                "childDefault": {},
                "childParameters": [
                    {
                        **DEFAULT_SERIALIZED_MODULE_PARAM,
                        "idName": "hello2",
                        "type": "statictext",
                        "name": "Hello2 default",
                    }
                ],
            }
        ]
        self.assertEqual(result["param_fields"], expected)


class JsonizeI18nMessageTest(DbTestCaseWithModuleRegistry):
    def test_TODO_i18n(self):
        self.assertEqual(
            jsonize_i18n_message(
                TODO_i18n("hello"), mock_jsonize_context(locale_id="en")
            ),
            "hello",
        )

    def test_source_None_message_exists_in_given_locale(self):
        en_catalog = Catalog()
        en_catalog.add("id", string="Hello")
        el_catalog = Catalog()
        el_catalog.add("id", string="Hey")
        with mock_app_catalogs({"el": el_catalog, "en": en_catalog}):
            self.assertEqual(
                jsonize_i18n_message(
                    I18nMessage("id", {}, None),
                    JsonizeModuleContext("el", "testme", None),
                ),
                "Hey",
            )

    def test_source_None_message_exists_only_in_default_locale(self):
        def mocker(locale):
            catalog = Catalog()
            if locale == "en":
                catalog.add("id", string="Hello")
            return catalog

        en_catalog = Catalog()
        en_catalog.add("id", string="Hello")
        el_catalog = Catalog()
        with mock_app_catalogs({"el": el_catalog, "en": en_catalog}):
            self.assertEqual(
                jsonize_i18n_message(
                    I18nMessage("id", {}, None),
                    JsonizeModuleContext("el", "testme", None),
                ),
                "Hello",
            )

    def test_source_None_message_exists_in_no_locales(self):
        en_catalog = Catalog()
        el_catalog = Catalog()
        with mock_app_catalogs({"el": el_catalog, "en": en_catalog}):
            with self.assertLogs(level=logging.ERROR):
                result = jsonize_i18n_message(
                    I18nMessage("messageid", {}, None),
                    JsonizeModuleContext("el", "testme", None),
                )
                self.assertRegex(result, "messageid")

    def test_source_None_default_message_incorrect_format(self):
        en_catalog = Catalog()
        en_catalog.add("id", string="Hello {a b}")
        el_catalog = Catalog()
        with mock_app_catalogs({"el": el_catalog, "en": en_catalog}):
            with self.assertLogs(level=logging.ERROR):
                result = jsonize_i18n_message(
                    I18nMessage("messageid", {}, None),
                    JsonizeModuleContext("el", "testme", None),
                )
                self.assertRegex(result, "messageid")

    def test_source_module_message_exists_in_given_locale(self):
        catalog = Catalog()
        catalog.add("messageid", string="Translated")
        default_catalog = Catalog()
        default_catalog.add("messageid", string="Default")
        module_zipfile = create_module_zipfile_with_catalogs(
            "testme", {"el": catalog, "en": default_catalog}
        )
        self.assertEqual(
            jsonize_i18n_message(
                I18nMessage("messageid", {}, "module"),
                JsonizeModuleContext("el", "testme", module_zipfile),
            ),
            "Translated",
        )

    def test_source_module_message_exists_only_in_default_locale(self):
        catalog = Catalog()
        default_catalog = Catalog()
        default_catalog.add("messageid", string="Default")
        module_zipfile = create_module_zipfile_with_catalogs(
            "testme", {"el": catalog, "en": default_catalog}
        )
        self.assertEqual(
            jsonize_i18n_message(
                I18nMessage("messageid", {}, "module"),
                JsonizeModuleContext("el", "testme", module_zipfile),
            ),
            "Default",
        )

    def test_source_module_message_exists_in_no_locales(self):
        catalog = Catalog()
        default_catalog = Catalog()
        module_zipfile = create_module_zipfile_with_catalogs(
            "testme", {"el": catalog, "en": default_catalog}
        )
        with self.assertLogs(level=logging.ERROR):
            result = jsonize_i18n_message(
                I18nMessage("messageid", {}, "module"),
                JsonizeModuleContext("el", "testme", module_zipfile),
            )
            self.assertRegex(result, "messageid")

    def test_source_module_default_message_incorrect_format(self):
        catalog = Catalog()
        default_catalog = Catalog()
        default_catalog.add("id", string="Hello {a b}")
        module_zipfile = create_module_zipfile_with_catalogs(
            "testme", {"el": catalog, "en": default_catalog}
        )
        with self.assertLogs(level=logging.ERROR):
            result = jsonize_i18n_message(
                I18nMessage("messageid", {}, "module"),
                JsonizeModuleContext("el", "testme", module_zipfile),
            )
            self.assertRegex(result, "messageid")

    def test_source_module_module_not_internationalized(self):
        module_zipfile = create_module_zipfile_with_catalogs("testme", {})
        with self.assertLogs(level=logging.ERROR):
            result = jsonize_i18n_message(
                I18nMessage("messageid", {}, "module"),
                JsonizeModuleContext("el", "testme", module_zipfile),
            )
            self.assertRegex(result, "messageid")

    def test_source_module_module_zipfile_not_in_context(self):
        with self.assertLogs(level=logging.ERROR):
            result = jsonize_i18n_message(
                I18nMessage("messageid", {}, "module"),
                JsonizeModuleContext("el", "testme", None),
            )
            self.assertRegex(result, "messageid")

    def test_source_cjwmodule_message_exists_in_given_locale(self):
        catalog = Catalog()
        catalog.add("messageid", string="Translated")
        default_catalog = Catalog()
        default_catalog.add("messageid", string="Default")
        with mock_cjwmodule_catalogs({"el": catalog, "en": default_catalog}):
            self.assertEqual(
                jsonize_i18n_message(
                    I18nMessage("messageid", {}, "cjwmodule"),
                    JsonizeModuleContext("el", "testme", None),
                ),
                "Translated",
            )

    def test_source_cjwmodule_message_exists_only_in_default_locale(self):
        catalog = Catalog()
        default_catalog = Catalog()
        default_catalog.add("messageid", string="Default")
        with mock_cjwmodule_catalogs({"el": catalog, "en": default_catalog}):
            self.assertEqual(
                jsonize_i18n_message(
                    I18nMessage("messageid", {}, "cjwmodule"),
                    JsonizeModuleContext("el", "testme", None),
                ),
                "Default",
            )

    def test_source_cjwmodule_message_exists_in_no_locales(self):
        catalog = Catalog()
        default_catalog = Catalog()
        with mock_cjwmodule_catalogs({"el": catalog, "en": default_catalog}):
            with self.assertLogs(level=logging.ERROR):
                result = jsonize_i18n_message(
                    I18nMessage("messageid", {}, "cjwmodule"),
                    JsonizeModuleContext("el", "testme", None),
                )
                self.assertRegex(result, "messageid")

    def test_source_cjwmodule_default_message_incorrect_format(self):
        catalog = Catalog()
        default_catalog = Catalog()
        default_catalog.add("id", string="Hello {a b}")
        with mock_cjwmodule_catalogs({"el": catalog, "en": default_catalog}):
            with self.assertLogs(level=logging.ERROR):
                result = jsonize_i18n_message(
                    I18nMessage("messageid", {}, "cjwmodule"),
                    JsonizeModuleContext("el", "testme", None),
                )
                self.assertRegex(result, "messageid")


class JsonizeBlocksTest(unittest.TestCase):
    def test_text_block(self):
        self.assertEqual(
            jsonize_clientside_update(
                Update(
                    blocks={"block-1": TextBlock(markdown="# header")},
                ),
                mock_jsonize_context(),
            ),
            {
                "updateBlocks": {"block-1": {"type": "text", "markdown": "# header"}},
            },
        )

    def test_chart_block(self):
        self.assertEqual(
            jsonize_clientside_update(
                Update(blocks={"block-1": ChartBlock(step_slug="step-1")}),
                mock_jsonize_context(),
            ),
            {"updateBlocks": {"block-1": {"type": "chart", "stepSlug": "step-1"}}},
        )

    def test_table_block(self):
        self.assertEqual(
            jsonize_clientside_update(
                Update(blocks={"block-1": TableBlock(tab_slug="tab-1")}),
                mock_jsonize_context(),
            ),
            {"updateBlocks": {"block-1": {"type": "table", "tabSlug": "tab-1"}}},
        )
