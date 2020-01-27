import unittest
import logging
from cjwkernel.types import (
    I18nMessage,
    I18nMessageSource,
    QuickFix,
    QuickFixAction,
    RenderError,
)
from server.serializers import (
    jsonize_i18n_message,
    JsonizeContext,
    JsonizeModuleContext,
    jsonize_clientside_module,
    _jsonize_param_spec,
)
from cjworkbench.i18n.trans import MessageLocalizer
from unittest.mock import patch
from babel.messages.catalog import Catalog
from cjwstate.modules.types import ModuleSpec
from cjwstate.clientside import Module
from typing import Dict, Any


def mock_jsonize_context(
    user=None, session=None, locale_id=None, localizers={}, module_id=None
):
    if module_id:
        return JsonizeModuleContext(
            user=user,
            session=session,
            locale_id=locale_id,
            module_id=module_id,
            localizers=localizers,
        )
    else:
        return JsonizeContext(
            user=user, session=session, locale_id=locale_id, localizers=localizers
        )


def _jsonize_clientside_module_return(args: Dict[str, Any]) -> Dict[str, Any]:
    result = {
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
    result.update(args)
    return result


class JsonizeClientsideModuleTest(unittest.TestCase):
    def test_with_js(self):
        module = Module(
            ModuleSpec(
                **{
                    "id_name": "testme",
                    "name": "Test Module",
                    "category": "Clean",
                    "parameters": [],
                }
            ),
            "var js = 1; console.log(js)",
        )
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                localizers={
                    "module.testme": MessageLocalizer("el", Catalog(), Catalog())
                },
            ),
        )
        expected = _jsonize_clientside_module_return(
            {
                "id_name": "testme",
                "name": "Test Module",
                "category": "Clean",
                "js_module": "var js = 1; console.log(js)",
            }
        )
        self.assertDictEqual(result, expected)

    def test_no_params_translate(self):
        module = Module(
            ModuleSpec(
                **{
                    "id_name": "testme",
                    "name": "Test Module",
                    "category": "Clean",
                    "parameters": [],
                }
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
                localizers={
                    "module.testme": MessageLocalizer("el", catalog, default_catalog)
                },
            ),
        )
        expected = _jsonize_clientside_module_return(
            {"id_name": "testme", "name": "Translated name", "category": "Clean"}
        )
        self.assertDictEqual(result, expected)

    def test_no_params_translate_use_default_catalog(self):
        module = Module(
            ModuleSpec(
                **{
                    "id_name": "testme",
                    "name": "Test Module",
                    "category": "Clean",
                    "parameters": [],
                }
            ),
            "",
        )
        catalog = Catalog()
        default_catalog = Catalog()
        default_catalog.add("_spec.name", string="Default translated name")
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                localizers={
                    "module.testme": MessageLocalizer("el", catalog, default_catalog)
                },
            ),
        )
        expected = _jsonize_clientside_module_return(
            {
                "id_name": "testme",
                "name": "Default translated name",
                "category": "Clean",
            }
        )
        self.assertDictEqual(result, expected)

    def test_no_params_translate_empty_catalogs(self):
        module = Module(
            ModuleSpec(
                **{
                    "id_name": "testme",
                    "name": "Test Module",
                    "category": "Clean",
                    "parameters": [],
                }
            ),
            "",
        )
        catalog = Catalog()
        default_catalog = Catalog()
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                localizers={
                    "module.testme": MessageLocalizer("el", catalog, default_catalog)
                },
            ),
        )
        expected = _jsonize_clientside_module_return(
            {"id_name": "testme", "name": "Test Module", "category": "Clean"}
        )
        self.assertDictEqual(result, expected)

    # Tests that translatable catalog entries which are not in the spec are ignored
    def test_no_params_translate_superfluous_catalog(self):
        module = Module(
            ModuleSpec(
                **{
                    "id_name": "testme",
                    "name": "Test Module",
                    "category": "Clean",
                    "parameters": [],
                }
            ),
            "",
        )
        catalog = Catalog()
        default_catalog = Catalog()
        default_catalog.add("_spec.row_action_menu_entry_title", string="Title")
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                localizers={
                    "module.testme": MessageLocalizer("el", catalog, default_catalog)
                },
            ),
        )
        expected = _jsonize_clientside_module_return(
            {"id_name": "testme", "name": "Test Module", "category": "Clean"}
        )
        self.assertDictEqual(result, expected)

    def test_everything_except_parameters(self):
        module = Module(
            ModuleSpec(
                **{
                    "id_name": "testme",
                    "name": "Test Module",
                    "category": "Clean",
                    "parameters": [],
                    "description": "I do that",
                    "deprecated": {
                        "message": "Please use something else",
                        "end_date": "2030-12-31",
                    },
                    "icon": "url",
                    "link": "http://example.com/module",
                    "loads_data": False,
                    "uses_data": True,
                    "html_output": False,
                    "has_zen_mode": True,
                    "row_action_menu_entry_title": "Solve your problem",
                    "help_url": "testme",
                    "parameters_version": 3,
                }
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
                localizers={
                    "module.testme": MessageLocalizer("el", catalog, default_catalog)
                },
            ),
        )
        expected = _jsonize_clientside_module_return(
            {
                "id_name": "testme",
                "name": "Name translated",
                "category": "Clean",
                "param_fields": [],
                "description": "Description translated",
                "deprecated": {
                    "message": "Deprecated default",
                    "end_date": "2030-12-31",
                },
                "icon": "url",
                "loads_data": False,
                "uses_data": True,
                "has_html_output": False,
                "has_zen_mode": True,
                "row_action_menu_entry_title": "Action default",
                "help_url": "http://help.workbenchdata.com/testme",
            }
        )
        self.assertDictEqual(result, expected)

    def test_parameter_type_statictext(self):
        module = Module(
            ModuleSpec(
                **{
                    "id_name": "testme",
                    "name": "Test Module",
                    "category": "Clean",
                    "parameters": [
                        {
                            "id_name": "hello",
                            "type": "statictext",
                            "name": "Hello there!",
                        }
                    ],
                }
            ),
            "",
        )
        catalog = Catalog()
        catalog.add("_spec.parameters.hello.name", string="Hello translated")
        default_catalog = Catalog()
        default_catalog.add("_spec.parameters.hello.name", string="Hello default")
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                localizers={
                    "module.testme": MessageLocalizer("el", catalog, default_catalog)
                },
            ),
        )
        expected = _jsonize_clientside_module_return(
            {
                "id_name": "testme",
                "name": "Test Module",
                "category": "Clean",
                "param_fields": [
                    {
                        "idName": "hello",
                        "type": "statictext",
                        "name": "Hello translated",
                        "visibleIf": None,
                    }
                ],
            }
        )
        self.assertDictEqual(result, expected)

    def test_parameter_type_string(self):
        module = Module(
            ModuleSpec(
                **{
                    "id_name": "testme",
                    "name": "Test Module",
                    "category": "Clean",
                    "parameters": [
                        {
                            "id_name": "hello",
                            "type": "string",
                            "name": "Hello there!",
                            "placeholder": "Hey",
                            "multiline": False,
                            "default": "H",
                        }
                    ],
                }
            ),
            "",
        )
        catalog = Catalog()
        catalog.add("_spec.parameters.hello.name", string="Hello translated")
        default_catalog = Catalog()
        default_catalog.add("_spec.parameters.hello.name", string="Hello default")
        default_catalog.add("_spec.parameters.hello.placeholder", string="Fill me")
        default_catalog.add("_spec.parameters.hello.default", string="Default")
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                localizers={
                    "module.testme": MessageLocalizer("el", catalog, default_catalog)
                },
            ),
        )
        expected = _jsonize_clientside_module_return(
            {
                "id_name": "testme",
                "name": "Test Module",
                "category": "Clean",
                "param_fields": [
                    {
                        "idName": "hello",
                        "type": "string",
                        "name": "Hello translated",
                        "placeholder": "Fill me",
                        "multiline": False,
                        "default": "Default",
                        "visibleIf": None,
                    }
                ],
            }
        )
        self.assertDictEqual(result, expected)

    def test_parameter_type_integer(self):
        module = Module(
            ModuleSpec(
                **{
                    "id_name": "testme",
                    "name": "Test Module",
                    "category": "Clean",
                    "parameters": [
                        {
                            "id_name": "hello",
                            "type": "integer",
                            "name": "Hello there!",
                            "placeholder": "Hey",
                            "default": 3,
                        }
                    ],
                }
            ),
            "",
        )
        catalog = Catalog()
        catalog.add("_spec.parameters.hello.name", string="Hello translated")
        default_catalog = Catalog()
        default_catalog.add("_spec.parameters.hello.name", string="Hello default")
        default_catalog.add("_spec.parameters.hello.placeholder", string="Fill me")
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                localizers={
                    "module.testme": MessageLocalizer("el", catalog, default_catalog)
                },
            ),
        )
        expected = _jsonize_clientside_module_return(
            {
                "id_name": "testme",
                "name": "Test Module",
                "category": "Clean",
                "param_fields": [
                    {
                        "idName": "hello",
                        "type": "integer",
                        "name": "Hello translated",
                        "placeholder": "Fill me",
                        "default": 3,
                        "visibleIf": None,
                    }
                ],
            }
        )
        self.assertDictEqual(result, expected)

    def test_parameter_type_float(self):
        module = Module(
            ModuleSpec(
                **{
                    "id_name": "testme",
                    "name": "Test Module",
                    "category": "Clean",
                    "parameters": [
                        {
                            "id_name": "hello",
                            "type": "float",
                            "name": "Hello there!",
                            "placeholder": "Hey",
                            "default": 3.4,
                        }
                    ],
                }
            ),
            "",
        )
        catalog = Catalog()
        catalog.add("_spec.parameters.hello.name", string="Hello translated")
        default_catalog = Catalog()
        default_catalog.add("_spec.parameters.hello.name", string="Hello default")
        default_catalog.add("_spec.parameters.hello.placeholder", string="Fill me")
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                localizers={
                    "module.testme": MessageLocalizer("el", catalog, default_catalog)
                },
            ),
        )
        expected = _jsonize_clientside_module_return(
            {
                "id_name": "testme",
                "name": "Test Module",
                "category": "Clean",
                "param_fields": [
                    {
                        "idName": "hello",
                        "type": "float",
                        "name": "Hello translated",
                        "placeholder": "Fill me",
                        "default": 3.4,
                        "visibleIf": None,
                    }
                ],
            }
        )
        self.assertDictEqual(result, expected)

    def test_parameter_type_checkbox(self):
        module = Module(
            ModuleSpec(
                **{
                    "id_name": "testme",
                    "name": "Test Module",
                    "category": "Clean",
                    "parameters": [
                        {
                            "id_name": "hello",
                            "type": "checkbox",
                            "name": "Hello there!",
                            "default": True,
                        }
                    ],
                }
            ),
            "",
        )
        catalog = Catalog()
        catalog.add("_spec.parameters.hello.name", string="Hello translated")
        default_catalog = Catalog()
        default_catalog.add("_spec.parameters.hello.name", string="Hello default")
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                localizers={
                    "module.testme": MessageLocalizer("el", catalog, default_catalog)
                },
            ),
        )
        expected = _jsonize_clientside_module_return(
            {
                "id_name": "testme",
                "name": "Test Module",
                "category": "Clean",
                "param_fields": [
                    {
                        "idName": "hello",
                        "type": "checkbox",
                        "name": "Hello translated",
                        "default": True,
                        "visibleIf": None,
                    }
                ],
            }
        )
        self.assertDictEqual(result, expected)

    def test_parameter_type_menu(self):
        module = Module(
            ModuleSpec(
                **{
                    "id_name": "testme",
                    "name": "Test Module",
                    "category": "Clean",
                    "parameters": [
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
                }
            ),
            "",
        )
        catalog = Catalog()
        catalog.add("_spec.parameters.hello.name", string="Hello translated")
        catalog.add(
            "_spec.parameters.hello.options.first.label", string="First translated"
        )
        default_catalog = Catalog()
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
                localizers={
                    "module.testme": MessageLocalizer("el", catalog, default_catalog)
                },
            ),
        )
        expected = _jsonize_clientside_module_return(
            {
                "id_name": "testme",
                "name": "Test Module",
                "category": "Clean",
                "param_fields": [
                    {
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
                        "visibleIf": None,
                    }
                ],
            }
        )
        self.assertDictEqual(result, expected)

    def test_parameter_type_radio(self):
        module = Module(
            ModuleSpec(
                **{
                    "id_name": "testme",
                    "name": "Test Module",
                    "category": "Clean",
                    "parameters": [
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
                }
            ),
            "",
        )
        catalog = Catalog()
        catalog.add("_spec.parameters.hello.name", string="Hello translated")
        catalog.add(
            "_spec.parameters.hello.options.first.label", string="First translated"
        )
        default_catalog = Catalog()
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
                localizers={
                    "module.testme": MessageLocalizer("el", catalog, default_catalog)
                },
            ),
        )
        expected = _jsonize_clientside_module_return(
            {
                "id_name": "testme",
                "name": "Test Module",
                "category": "Clean",
                "param_fields": [
                    {
                        "idName": "hello",
                        "type": "radio",
                        "name": "Hello translated",
                        "options": [
                            {"label": "First translated", "value": "first"},
                            {"label": "Second default", "value": True},
                        ],
                        "default": "first",
                        "visibleIf": None,
                    }
                ],
            }
        )
        self.assertDictEqual(result, expected)

    def test_parameter_type_numberformat(self):
        module = Module(
            ModuleSpec(
                **{
                    "id_name": "testme",
                    "name": "Test Module",
                    "category": "Clean",
                    "parameters": [
                        {
                            "id_name": "hello",
                            "type": "numberformat",
                            "name": "Hello there!",
                            "placeholder": "Fill me",
                        }
                    ],
                }
            ),
            "",
        )
        catalog = Catalog()
        catalog.add("_spec.parameters.hello.name", string="Hello translated")
        default_catalog = Catalog()
        default_catalog.add("_spec.parameters.hello.name", string="Hello default")
        default_catalog.add(
            "_spec.parameters.hello.placeholder", string="Fill me default"
        )
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                localizers={
                    "module.testme": MessageLocalizer("el", catalog, default_catalog)
                },
            ),
        )
        expected = _jsonize_clientside_module_return(
            {
                "id_name": "testme",
                "name": "Test Module",
                "category": "Clean",
                "param_fields": [
                    {
                        "idName": "hello",
                        "type": "numberformat",
                        "name": "Hello translated",
                        "placeholder": "Fill me default",
                        "visibleIf": None,
                        "default": "{:,}",
                    }
                ],
            }
        )
        self.assertDictEqual(result, expected)

    def test_parameter_type_column(self):
        module = Module(
            ModuleSpec(
                **{
                    "id_name": "testme",
                    "name": "Test Module",
                    "category": "Clean",
                    "parameters": [
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
                }
            ),
            "",
        )
        catalog = Catalog()
        catalog.add("_spec.parameters.hello.name", string="Hello translated")
        default_catalog = Catalog()
        default_catalog.add("_spec.parameters.hello.name", string="Hello default")
        default_catalog.add(
            "_spec.parameters.hello.placeholder", string="Fill me default"
        )
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                localizers={
                    "module.testme": MessageLocalizer("el", catalog, default_catalog)
                },
            ),
        )
        expected = _jsonize_clientside_module_return(
            {
                "id_name": "testme",
                "name": "Test Module",
                "category": "Clean",
                "param_fields": [
                    {
                        "idName": "hello",
                        "type": "column",
                        "name": "Hello translated",
                        "placeholder": "Fill me default",
                        "columnTypes": ["text"],
                        "tabParameter": "tab",
                        "visibleIf": None,
                    },
                    {
                        "idName": "tab",
                        "type": "tab",
                        "name": "Hello there 2!",
                        "placeholder": "",
                        "visibleIf": None,
                    },
                ],
            }
        )
        self.assertDictEqual(result, expected)

    def test_parameter_type_multicolumn(self):
        module = Module(
            ModuleSpec(
                **{
                    "id_name": "testme",
                    "name": "Test Module",
                    "category": "Clean",
                    "parameters": [
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
                }
            ),
            "",
        )
        catalog = Catalog()
        catalog.add("_spec.parameters.hello.name", string="Hello translated")
        default_catalog = Catalog()
        default_catalog.add("_spec.parameters.hello.name", string="Hello default")
        default_catalog.add(
            "_spec.parameters.hello.placeholder", string="Fill me default"
        )
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                localizers={
                    "module.testme": MessageLocalizer("el", catalog, default_catalog)
                },
            ),
        )
        expected = _jsonize_clientside_module_return(
            {
                "id_name": "testme",
                "name": "Test Module",
                "category": "Clean",
                "param_fields": [
                    {
                        "idName": "hello",
                        "type": "multicolumn",
                        "name": "Hello translated",
                        "placeholder": "Fill me default",
                        "columnTypes": ["text"],
                        "tabParameter": "tab",
                        "visibleIf": None,
                    },
                    {
                        "idName": "tab",
                        "type": "tab",
                        "name": "Hello there 2!",
                        "placeholder": "",
                        "visibleIf": None,
                    },
                ],
            }
        )
        self.assertDictEqual(result, expected)

    def test_parameter_type_tab(self):
        module = Module(
            ModuleSpec(
                **{
                    "id_name": "testme",
                    "name": "Test Module",
                    "category": "Clean",
                    "parameters": [
                        {
                            "id_name": "hello",
                            "type": "tab",
                            "name": "Hello there!",
                            "placeholder": "Fill me",
                        }
                    ],
                }
            ),
            "",
        )
        catalog = Catalog()
        catalog.add("_spec.parameters.hello.name", string="Hello translated")
        default_catalog = Catalog()
        default_catalog.add("_spec.parameters.hello.name", string="Hello default")
        default_catalog.add(
            "_spec.parameters.hello.placeholder", string="Fill me default"
        )
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                localizers={
                    "module.testme": MessageLocalizer("el", catalog, default_catalog)
                },
            ),
        )
        expected = _jsonize_clientside_module_return(
            {
                "id_name": "testme",
                "name": "Test Module",
                "category": "Clean",
                "param_fields": [
                    {
                        "idName": "hello",
                        "type": "tab",
                        "name": "Hello translated",
                        "placeholder": "Fill me default",
                        "visibleIf": None,
                    }
                ],
            }
        )
        self.assertDictEqual(result, expected)

    def test_parameter_type_multitab(self):
        module = Module(
            ModuleSpec(
                **{
                    "id_name": "testme",
                    "name": "Test Module",
                    "category": "Clean",
                    "parameters": [
                        {
                            "id_name": "hello",
                            "type": "multitab",
                            "name": "Hello there!",
                            "placeholder": "Fill me",
                        }
                    ],
                }
            ),
            "",
        )
        catalog = Catalog()
        catalog.add("_spec.parameters.hello.name", string="Hello translated")
        default_catalog = Catalog()
        default_catalog.add("_spec.parameters.hello.name", string="Hello default")
        default_catalog.add(
            "_spec.parameters.hello.placeholder", string="Fill me default"
        )
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                localizers={
                    "module.testme": MessageLocalizer("el", catalog, default_catalog)
                },
            ),
        )
        expected = _jsonize_clientside_module_return(
            {
                "id_name": "testme",
                "name": "Test Module",
                "category": "Clean",
                "param_fields": [
                    {
                        "idName": "hello",
                        "type": "multitab",
                        "name": "Hello translated",
                        "placeholder": "Fill me default",
                        "visibleIf": None,
                    }
                ],
            }
        )
        self.assertDictEqual(result, expected)

    def test_parameter_type_multichartseries(self):
        module = Module(
            ModuleSpec(
                **{
                    "id_name": "testme",
                    "name": "Test Module",
                    "category": "Clean",
                    "parameters": [
                        {
                            "id_name": "hello",
                            "type": "multichartseries",
                            "name": "Hello there!",
                        }
                    ],
                }
            ),
            "",
        )
        catalog = Catalog()
        catalog.add("_spec.parameters.hello.name", string="Hello translated")
        default_catalog = Catalog()
        default_catalog.add("_spec.parameters.hello.name", string="Hello default")
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                localizers={
                    "module.testme": MessageLocalizer("el", catalog, default_catalog)
                },
            ),
        )
        expected = _jsonize_clientside_module_return(
            {
                "id_name": "testme",
                "name": "Test Module",
                "category": "Clean",
                "param_fields": [
                    {
                        "idName": "hello",
                        "type": "multichartseries",
                        "placeholder": "",
                        "name": "Hello translated",
                        "visibleIf": None,
                    }
                ],
            }
        )
        self.assertDictEqual(result, expected)

    def test_parameter_type_secret_string(self):
        module = Module(
            ModuleSpec(
                **{
                    "id_name": "testme",
                    "name": "Test Module",
                    "category": "Clean",
                    "parameters": [
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
                }
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
                localizers={
                    "module.testme": MessageLocalizer("el", catalog, default_catalog)
                },
            ),
        )
        expected = _jsonize_clientside_module_return(
            {
                "id_name": "testme",
                "name": "Test Module",
                "category": "Clean",
                "param_fields": [
                    {
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
                        "visibleIf": None,
                    }
                ],
            }
        )
        self.assertDictEqual(result, expected)

    def test_parameter_type_secret_oauth2(self):
        module = Module(
            ModuleSpec(
                **{
                    "id_name": "testme",
                    "name": "Test Module",
                    "category": "Clean",
                    "parameters": [
                        {
                            "id_name": "hello",
                            "type": "secret",
                            "secret_logic": {"provider": "oauth2", "service": "google"},
                        }
                    ],
                }
            ),
            "",
        )
        catalog = Catalog()
        default_catalog = Catalog()
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                localizers={
                    "module.testme": MessageLocalizer("el", catalog, default_catalog)
                },
            ),
        )
        expected = _jsonize_clientside_module_return(
            {
                "id_name": "testme",
                "name": "Test Module",
                "category": "Clean",
                "param_fields": [
                    {
                        "idName": "hello",
                        "type": "secret",
                        "secretLogic": {"provider": "oauth2", "service": "google"},
                        "visibleIf": None,
                    }
                ],
            }
        )
        self.assertDictEqual(result, expected)

    def test_parameter_type_secret_oauth1a(self):
        module = Module(
            ModuleSpec(
                **{
                    "id_name": "testme",
                    "name": "Test Module",
                    "category": "Clean",
                    "parameters": [
                        {
                            "id_name": "hello",
                            "type": "secret",
                            "secret_logic": {
                                "provider": "oauth1a",
                                "service": "twitter",
                            },
                        }
                    ],
                }
            ),
            "",
        )
        catalog = Catalog()
        default_catalog = Catalog()
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                localizers={
                    "module.testme": MessageLocalizer("el", catalog, default_catalog)
                },
            ),
        )
        expected = _jsonize_clientside_module_return(
            {
                "id_name": "testme",
                "name": "Test Module",
                "category": "Clean",
                "param_fields": [
                    {
                        "idName": "hello",
                        "type": "secret",
                        "secretLogic": {"provider": "oauth1a", "service": "twitter"},
                        "visibleIf": None,
                    }
                ],
            }
        )
        self.assertDictEqual(result, expected)

    def test_parameter_type_gdrivefile(self):
        module = Module(
            ModuleSpec(
                **{
                    "id_name": "testme",
                    "name": "Test Module",
                    "category": "Clean",
                    "parameters": [
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
                }
            ),
            "",
        )
        catalog = Catalog()
        default_catalog = Catalog()
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                localizers={
                    "module.testme": MessageLocalizer("el", catalog, default_catalog)
                },
            ),
        )
        expected = _jsonize_clientside_module_return(
            {
                "id_name": "testme",
                "name": "Test Module",
                "category": "Clean",
                "param_fields": [
                    {
                        "idName": "google",
                        "type": "secret",
                        "secretLogic": {"provider": "oauth2", "service": "google"},
                        "visibleIf": None,
                    },
                    {
                        "idName": "hello2",
                        "type": "gdrivefile",
                        "name": "",
                        "secretParameter": "google",
                        "visibleIf": None,
                    },
                ],
            }
        )
        self.assertDictEqual(result, expected)

    def test_parameter_type_file(self):
        module = Module(
            ModuleSpec(
                **{
                    "id_name": "testme",
                    "name": "Test Module",
                    "category": "Clean",
                    "parameters": [{"id_name": "hello", "type": "file"}],
                }
            ),
            "",
        )
        catalog = Catalog()
        default_catalog = Catalog()
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                localizers={
                    "module.testme": MessageLocalizer("el", catalog, default_catalog)
                },
            ),
        )
        expected = _jsonize_clientside_module_return(
            {
                "id_name": "testme",
                "name": "Test Module",
                "category": "Clean",
                "param_fields": [
                    {"idName": "hello", "type": "file", "visibleIf": None}
                ],
            }
        )
        self.assertDictEqual(result, expected)

    def test_parameter_type_custom(self):
        module = Module(
            ModuleSpec(
                **{
                    "id_name": "testme",
                    "name": "Test Module",
                    "category": "Clean",
                    "parameters": [
                        {"id_name": "hello", "type": "custom", "name": "Hello there!"}
                    ],
                }
            ),
            "",
        )
        catalog = Catalog()
        catalog.add("_spec.parameters.hello.name", string="Hello translated")
        default_catalog = Catalog()
        default_catalog.add("_spec.parameters.hello.name", string="Hello default")
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                localizers={
                    "module.testme": MessageLocalizer("el", catalog, default_catalog)
                },
            ),
        )
        expected = _jsonize_clientside_module_return(
            {
                "id_name": "testme",
                "name": "Test Module",
                "category": "Clean",
                "param_fields": [
                    {
                        "idName": "hello",
                        "type": "custom",
                        "default": "",
                        "name": "Hello translated",
                        "visibleIf": None,
                    }
                ],
            }
        )
        self.assertDictEqual(result, expected)

    def test_parameter_type_list(self):
        module = Module(
            ModuleSpec(
                **{
                    "id_name": "testme",
                    "name": "Test Module",
                    "category": "Clean",
                    "parameters": [
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
                }
            ),
            "",
        )
        catalog = Catalog()
        catalog.add("_spec.parameters.hello.name", string="Hello translated")
        default_catalog = Catalog()
        default_catalog.add("_spec.parameters.hello.name", string="Hello default")
        default_catalog.add(
            "_spec.parameters.hello.child_parameters.hello2.name",
            string="Hello2 default",
        )
        result = jsonize_clientside_module(
            module,
            mock_jsonize_context(
                locale_id="el",
                localizers={
                    "module.testme": MessageLocalizer("el", catalog, default_catalog)
                },
            ),
        )
        expected = _jsonize_clientside_module_return(
            {
                "id_name": "testme",
                "name": "Test Module",
                "category": "Clean",
                "param_fields": [
                    {
                        "idName": "hello",
                        "type": "list",
                        "name": "Hello translated",
                        "childDefault": {},
                        "childParameters": [
                            {
                                "idName": "hello2",
                                "type": "statictext",
                                "name": "Hello2 default",
                                "visibleIf": None,
                            }
                        ],
                        "visibleIf": None,
                    }
                ],
            }
        )
        self.assertDictEqual(result, expected)


class JsonizeI18nMessageTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        MessageLocalizer.for_application_messages.cache_clear()

    def tearDown(self):
        MessageLocalizer.for_application_messages.cache_clear()
        super().tearDown()

    def test_TODO_i18n(self):
        self.assertEqual(
            jsonize_i18n_message(
                I18nMessage.TODO_i18n("hello"), mock_jsonize_context(locale_id="en")
            ),
            "hello",
        )

    def test_source_None_message_exists_in_given_locale(self):
        def mock_app_catalogs(locale):
            catalog = Catalog()
            if locale == "en":
                catalog.add("id", string="Hello")
            else:
                catalog.add("id", string="Hey")
            return catalog

        with patch("cjworkbench.i18n.trans.load_catalog", mock_app_catalogs):
            self.assertEqual(
                jsonize_i18n_message(
                    I18nMessage("id"), mock_jsonize_context(locale_id="el")
                ),
                "Hey",
            )

    def test_source_None_message_exists_only_in_default_locale(self):
        def mock_app_catalogs(locale):
            catalog = Catalog()
            if locale == "en":
                catalog.add("id", string="Hello")
            return catalog

        with patch("cjworkbench.i18n.trans.load_catalog", mock_app_catalogs):
            self.assertEqual(
                jsonize_i18n_message(
                    I18nMessage("id"), mock_jsonize_context(locale_id="el")
                ),
                "Hello",
            )

    def test_source_None_message_exists_in_no_locales(self):
        def mock_app_catalogs(locale):
            return Catalog()

        with patch("cjworkbench.i18n.trans.load_catalog", mock_app_catalogs):
            with self.assertLogs(level=logging.ERROR):
                result = jsonize_i18n_message(
                    I18nMessage("messageid"), mock_jsonize_context(locale_id="el")
                )
                self.assertRegex(result, "messageid")

    def test_source_None_default_message_incorrect_format(self):
        def mock_app_catalogs(locale):
            catalog = Catalog()
            if locale == "en":
                catalog.add("id", string="Hello {a b}")
            return catalog

        with patch("cjworkbench.i18n.trans.load_catalog", mock_app_catalogs):
            with self.assertLogs(level=logging.ERROR):
                result = jsonize_i18n_message(
                    I18nMessage("messageid"), mock_jsonize_context(locale_id="el")
                )
                self.assertRegex(result, "messageid")

    def test_source_module_message_exists_in_given_locale(self):
        catalog = Catalog()
        catalog.add("messageid", string="Translated")
        default_catalog = Catalog()
        default_catalog.add("messageid", string="Default")
        self.assertEqual(
            jsonize_i18n_message(
                I18nMessage("messageid", source=I18nMessageSource.Module("testmodule")),
                mock_jsonize_context(
                    locale_id="el",
                    localizers={
                        "module.testmodule": MessageLocalizer(
                            "el", catalog, default_catalog
                        )
                    },
                ),
            ),
            "Translated",
        )

    def test_source_module_message_exists_only_in_default_locale(self):
        catalog = Catalog()
        default_catalog = Catalog()
        default_catalog.add("messageid", string="Default")
        self.assertEqual(
            jsonize_i18n_message(
                I18nMessage("messageid", source=I18nMessageSource.Module("testmodule")),
                mock_jsonize_context(
                    locale_id="el",
                    localizers={
                        "module.testmodule": MessageLocalizer(
                            "el", catalog, default_catalog
                        )
                    },
                ),
            ),
            "Default",
        )

    def test_source_module_message_exists_in_no_locales(self):
        catalog = Catalog()
        default_catalog = Catalog()
        with self.assertLogs(level=logging.ERROR):
            result = jsonize_i18n_message(
                I18nMessage("messageid", source=I18nMessageSource.Module("testmodule")),
                mock_jsonize_context(
                    locale_id="el",
                    localizers={
                        "module.testmodule": MessageLocalizer(
                            "el", catalog, default_catalog
                        )
                    },
                ),
            )
            self.assertRegex(result, "messageid")

    def test_source_module_default_message_incorrect_format(self):
        catalog = Catalog()
        default_catalog = Catalog()
        default_catalog.add("id", string="Hello {a b}")
        with self.assertLogs(level=logging.ERROR):
            result = jsonize_i18n_message(
                I18nMessage("messageid", source=I18nMessageSource.Module("testmodule")),
                mock_jsonize_context(
                    locale_id="el",
                    localizers={
                        "module.testmodule": MessageLocalizer(
                            "el", catalog, default_catalog
                        )
                    },
                ),
            )
            self.assertRegex(result, "messageid")

    def test_source_module_no_module_localizer_found(self):
        catalog = Catalog()
        default_catalog = Catalog()
        default_catalog.add("id", string="Hello {a b}")
        with self.assertLogs(level=logging.ERROR):
            result = jsonize_i18n_message(
                I18nMessage("messageid", source=I18nMessageSource.Module("testmodule")),
                mock_jsonize_context(locale_id="el"),
            )
            self.assertRegex(result, "messageid")
