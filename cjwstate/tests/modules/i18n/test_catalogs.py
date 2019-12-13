from cjworkbench.tests.test_catalogs import CatalogTest
from babel.messages.catalog import Catalog
from cjwstate.modules.module_loader import ModuleSpec, validate_module_spec
from cjwstate.modules.i18n.catalogs import _build_source_catalog
from typing import Dict, Any


def _make_module_spec(spec: Dict[str, Any]):
    validate_module_spec(spec)
    return ModuleSpec(**spec)


class BuildSourceCatalogSpecTest(CatalogTest):
    def test_only_required(self):
        spec = _make_module_spec(
            {
                "id_name": "testme",
                "name": "Test Module",
                "category": "Clean",
                "parameters": [],
            }
        )
        result = _build_source_catalog(spec)
        expected = Catalog("en")
        expected.add("_spec.name", string="Test Module")
        self.assertCatalogsDeeplyEqual(result, expected)

    def test_everything_except_parameters(self):
        spec = _make_module_spec(
            {
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
                "help_url": "/testme",
                "parameters_version": 3,
            }
        )
        result = _build_source_catalog(spec)
        expected = Catalog("en")
        expected.add("_spec.name", string="Test Module")
        expected.add("_spec.description", string="I do that")
        expected.add("_spec.deprecated.message", string="Please use something else")
        expected.add("_spec.row_action_menu_entry_title", string="Solve your problem")
        self.assertCatalogsDeeplyEqual(result, expected)

    def test_parameter_type_statictext(self):
        spec = _make_module_spec(
            {
                "id_name": "testme",
                "name": "Test Module",
                "category": "Clean",
                "parameters": [
                    {"id_name": "hello", "type": "statictext", "name": "Hello there!"}
                ],
            }
        )
        result = _build_source_catalog(spec)
        expected = Catalog("en")
        expected.add("_spec.name", string="Test Module")
        expected.add("_spec.parameters.hello.name", string="Hello there!")
        self.assertCatalogsDeeplyEqual(result, expected)

    def test_parameter_type_string(self):
        spec = _make_module_spec(
            {
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
        )
        result = _build_source_catalog(spec)
        expected = Catalog("en")
        expected.add("_spec.name", string="Test Module")
        expected.add("_spec.parameters.hello.name", string="Hello there!")
        expected.add("_spec.parameters.hello.placeholder", string="Hey")
        expected.add("_spec.parameters.hello.default", string="H")
        self.assertCatalogsDeeplyEqual(result, expected)

    def test_parameter_type_integer(self):
        spec = _make_module_spec(
            {
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
        )
        result = _build_source_catalog(spec)
        expected = Catalog("en")
        expected.add("_spec.name", string="Test Module")
        expected.add("_spec.parameters.hello.name", string="Hello there!")
        expected.add("_spec.parameters.hello.placeholder", string="Hey")
        self.assertCatalogsDeeplyEqual(result, expected)

    def test_parameter_type_float(self):
        spec = _make_module_spec(
            {
                "id_name": "testme",
                "name": "Test Module",
                "category": "Clean",
                "parameters": [
                    {
                        "id_name": "hello",
                        "type": "float",
                        "name": "Hello there!",
                        "placeholder": "Hey",
                        "default": 3.14,
                    }
                ],
            }
        )
        result = _build_source_catalog(spec)
        expected = Catalog("en")
        expected.add("_spec.name", string="Test Module")
        expected.add("_spec.parameters.hello.name", string="Hello there!")
        expected.add("_spec.parameters.hello.placeholder", string="Hey")
        self.assertCatalogsDeeplyEqual(result, expected)

    def test_parameter_type_checkbox(self):
        spec = _make_module_spec(
            {
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
        )
        result = _build_source_catalog(spec)
        expected = Catalog("en")
        expected.add("_spec.name", string="Test Module")
        expected.add("_spec.parameters.hello.name", string="Hello there!")
        self.assertCatalogsDeeplyEqual(result, expected)

    def test_parameter_type_menu(self):
        spec = _make_module_spec(
            {
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
        )
        result = _build_source_catalog(spec)
        expected = Catalog("en")
        expected.add("_spec.name", string="Test Module")
        expected.add("_spec.parameters.hello.name", string="Hello there!")
        expected.add("_spec.parameters.hello.placeholder", string="Choose something...")
        expected.add("_spec.parameters.hello.options.first.label", string="First")
        expected.add("_spec.parameters.hello.options.second.label", string="Second")
        self.assertCatalogsDeeplyEqual(result, expected)

    def test_parameter_type_radio(self):
        spec = _make_module_spec(
            {
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
                            {"label": True, "value": "second"},
                        ],
                        "default": "first",
                    }
                ],
            }
        )
        result = _build_source_catalog(spec)
        expected = Catalog("en")
        expected.add("_spec.name", string="Test Module")
        expected.add("_spec.parameters.hello.name", string="Hello there!")
        expected.add("_spec.parameters.hello.options.first.label", string="First")
        expected.add("_spec.parameters.hello.options.True.label", string="Second")
        self.assertCatalogsDeeplyEqual(result, expected)

    def test_parameter_type_radio(self):
        spec = _make_module_spec(
            {
                "id_name": "testme",
                "name": "Test Module",
                "category": "Clean",
                "parameters": [
                    {"id_name": "hello", "type": "button", "name": "Hello there!"}
                ],
            }
        )
        result = _build_source_catalog(spec)
        expected = Catalog("en")
        expected.add("_spec.name", string="Test Module")
        expected.add("_spec.parameters.hello.name", string="Hello there!")
        self.assertCatalogsDeeplyEqual(result, expected)

    def test_parameter_type_numberformat(self):
        spec = _make_module_spec(
            {
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
        )
        result = _build_source_catalog(spec)
        expected = Catalog("en")
        expected.add("_spec.name", string="Test Module")
        expected.add("_spec.parameters.hello.name", string="Hello there!")
        expected.add("_spec.parameters.hello.placeholder", string="Fill me")
        self.assertCatalogsDeeplyEqual(result, expected)

    def test_parameter_type_column(self):
        spec = _make_module_spec(
            {
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
        )
        result = _build_source_catalog(spec)
        expected = Catalog("en")
        expected.add("_spec.name", string="Test Module")
        expected.add("_spec.parameters.hello.name", string="Hello there!")
        expected.add("_spec.parameters.hello.placeholder", string="Fill me")
        expected.add("_spec.parameters.tab.name", string="Hello there 2!")
        self.assertCatalogsDeeplyEqual(result, expected)

    def test_parameter_type_multicolumn(self):
        spec = _make_module_spec(
            {
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
        )
        result = _build_source_catalog(spec)
        expected = Catalog("en")
        expected.add("_spec.name", string="Test Module")
        expected.add("_spec.parameters.hello.name", string="Hello there!")
        expected.add("_spec.parameters.hello.placeholder", string="Fill me")
        expected.add("_spec.parameters.tab.name", string="Hello there 2!")
        self.assertCatalogsDeeplyEqual(result, expected)

    def test_parameter_type_tab(self):
        spec = _make_module_spec(
            {
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
        )
        result = _build_source_catalog(spec)
        expected = Catalog("en")
        expected.add("_spec.name", string="Test Module")
        expected.add("_spec.parameters.hello.name", string="Hello there!")
        expected.add("_spec.parameters.hello.placeholder", string="Fill me")
        self.assertCatalogsDeeplyEqual(result, expected)

    def test_parameter_type_multitab(self):
        spec = _make_module_spec(
            {
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
        )
        result = _build_source_catalog(spec)
        expected = Catalog("en")
        expected.add("_spec.name", string="Test Module")
        expected.add("_spec.parameters.hello.name", string="Hello there!")
        expected.add("_spec.parameters.hello.placeholder", string="Fill me")
        self.assertCatalogsDeeplyEqual(result, expected)

    def test_parameter_type_multichartseries(self):
        spec = _make_module_spec(
            {
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
        )
        result = _build_source_catalog(spec)
        expected = Catalog("en")
        expected.add("_spec.name", string="Test Module")
        expected.add("_spec.parameters.hello.name", string="Hello there!")
        self.assertCatalogsDeeplyEqual(result, expected)

    def test_parameter_type_secret_string(self):
        spec = _make_module_spec(
            {
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
        )
        result = _build_source_catalog(spec)
        expected = Catalog("en")
        expected.add("_spec.name", string="Test Module")
        expected.add("_spec.parameters.hello.secret_logic.label", string="Secret")
        expected.add("_spec.parameters.hello.secret_logic.help", string="Find it there")
        expected.add(
            "_spec.parameters.hello.secret_logic.help_url_prompt",
            string="Take me there",
        )
        expected.add(
            "_spec.parameters.hello.secret_logic.help_url",
            string="https://example.com/get_secret",
        )
        self.assertCatalogsDeeplyEqual(result, expected)

    def test_parameter_type_secret_oauth2(self):
        spec = _make_module_spec(
            {
                "id_name": "googlesheets",
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
        )
        result = _build_source_catalog(spec)
        expected = Catalog("en")
        expected.add("_spec.name", string="Test Module")
        self.assertCatalogsDeeplyEqual(result, expected)

    def test_parameter_type_secret_oauth1a(self):
        spec = _make_module_spec(
            {
                "id_name": "twitter",
                "name": "Test Module",
                "category": "Clean",
                "parameters": [
                    {
                        "id_name": "hello",
                        "type": "secret",
                        "secret_logic": {"provider": "oauth1a", "service": "twitter"},
                    }
                ],
            }
        )
        result = _build_source_catalog(spec)
        expected = Catalog("en")
        expected.add("_spec.name", string="Test Module")
        self.assertCatalogsDeeplyEqual(result, expected)

    def test_parameter_type_gdrivefile(self):
        spec = _make_module_spec(
            {
                "id_name": "googlesheets",
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
        )
        result = _build_source_catalog(spec)
        expected = Catalog("en")
        expected.add("_spec.name", string="Test Module")

        self.assertCatalogsDeeplyEqual(result, expected)

    def test_parameter_type_file(self):
        spec = _make_module_spec(
            {
                "id_name": "testme",
                "name": "Test Module",
                "category": "Clean",
                "parameters": [{"id_name": "hello", "type": "file"}],
            }
        )
        result = _build_source_catalog(spec)
        expected = Catalog("en")
        expected.add("_spec.name", string="Test Module")
        self.assertCatalogsDeeplyEqual(result, expected)

    def test_parameter_type_custom(self):
        spec = _make_module_spec(
            {
                "id_name": "testme",
                "name": "Test Module",
                "category": "Clean",
                "parameters": [
                    {"id_name": "hello", "type": "custom", "name": "Hello there!"}
                ],
            }
        )
        result = _build_source_catalog(spec)
        expected = Catalog("en")
        expected.add("_spec.name", string="Test Module")
        expected.add("_spec.parameters.hello.name", string="Hello there!")
        self.assertCatalogsDeeplyEqual(result, expected)

    def test_parameter_type_list(self):
        spec = _make_module_spec(
            {
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
        )
        result = _build_source_catalog(spec)
        expected = Catalog("en")
        expected.add("_spec.name", string="Test Module")
        expected.add("_spec.parameters.hello.name", string="Hello there!")
        expected.add(
            "_spec.parameters.hello.child_parameters.hello2.name",
            string="Hello there 2!",
        )
        self.assertCatalogsDeeplyEqual(result, expected)

    def test_ignore_empty(self):
        spec = _make_module_spec(
            {
                "id_name": "testme",
                "name": "Test Module",
                "description": "",
                "category": "Clean",
                "parameters": [
                    {
                        "id_name": "hello",
                        "type": "list",
                        "name": "",
                        "child_parameters": [
                            {"id_name": "hello2", "type": "statictext", "name": ""}
                        ],
                    },
                    {
                        "id_name": "hello3",
                        "type": "string",
                        "name": "Hello there!",
                        "placeholder": "",
                        "multiline": True,
                        "default": "",
                    },
                ],
            }
        )
        result = _build_source_catalog(spec)
        expected = Catalog("en")
        expected.add("_spec.name", string="Test Module")
        expected.add("_spec.parameters.hello3.name", string="Hello there!")
        self.assertCatalogsDeeplyEqual(result, expected)
