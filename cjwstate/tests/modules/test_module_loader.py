import unittest
from cjwstate.modules.module_loader import validate_module_spec


class ValidateModuleSpecTest(unittest.TestCase):
    def test_schema_errors(self):
        with self.assertRaises(ValueError) as cm:
            validate_module_spec(
                {
                    "name": "Hello",
                    "link": "not a link at all",
                    "loads_data": "NotABoolean",
                    "parameters": [],
                }
            )

        self.assertRegex(str(cm.exception), "'id_name' is a required property")
        self.assertRegex(str(cm.exception), "'category' is a required property")
        self.assertRegex(str(cm.exception), "'not a link at all' is not a 'uri'")
        self.assertRegex(str(cm.exception), "'NotABoolean' is not of type 'boolean'")

    def test_unique_params(self):
        with self.assertRaisesRegex(ValueError, "Param 'dup' appears twice"):
            validate_module_spec(
                {
                    "id_name": "id",
                    "name": "Name",
                    "category": "Clean",
                    "parameters": [
                        {"id_name": "dup", "type": "string"},
                        {"id_name": "original", "type": "string"},
                        {"id_name": "dup", "type": "string"},
                    ],
                }
            )

    def test_missing_menu_options(self):
        with self.assertRaises(ValueError):
            validate_module_spec(
                {
                    "id_name": "id",
                    "name": "Name",
                    "category": "Clean",
                    "parameters": [{"id_name": "menu", "type": "menu"}],
                }
            )

    def test_missing_radio_options(self):
        with self.assertRaises(ValueError):
            validate_module_spec(
                {
                    "id_name": "id",
                    "name": "Name",
                    "category": "Clean",
                    "parameters": [{"id_name": "radio", "type": "radio"}],
                }
            )

    def test_invalid_visible_if(self):
        with self.assertRaisesRegex(
            ValueError, "Param 'a' has visible_if id_name 'b', which does not exist"
        ):
            validate_module_spec(
                {
                    "id_name": "id",
                    "name": "Name",
                    "category": "Clean",
                    "parameters": [
                        {
                            "id_name": "a",
                            "type": "string",
                            "visible_if": {"id_name": "b", "value": True},
                        }
                    ],
                }
            )

    def test_valid_visible_if(self):
        # does not raise
        validate_module_spec(
            {
                "id_name": "id",
                "name": "Name",
                "category": "Clean",
                "parameters": [
                    {
                        "id_name": "a",
                        "type": "string",
                        "visible_if": {"id_name": "b", "value": True},
                    },
                    {"id_name": "b", "type": "string"},
                ],
            }
        )

    def test_valid_visible_if_menu_options(self):
        # does not raise
        validate_module_spec(
            {
                "id_name": "id",
                "name": "Name",
                "category": "Clean",
                "parameters": [
                    {
                        "id_name": "a",
                        "type": "string",
                        "visible_if": {"id_name": "b", "value": ["a", "b"]},
                    },
                    {
                        "id_name": "b",
                        "type": "menu",
                        "options": [
                            {"value": "a", "label": "A"},
                            "separator",
                            {"value": "b", "label": "B"},
                            {"value": "c", "label": "C"},
                        ],
                    },
                ],
            }
        )

    def test_invalid_visible_if_menu_options(self):
        with self.assertRaisesRegex(
            ValueError, "Param 'a' has visible_if values \\{'x'\\} not in 'b' options"
        ):
            validate_module_spec(
                {
                    "id_name": "id",
                    "name": "Name",
                    "category": "Clean",
                    "parameters": [
                        {
                            "id_name": "a",
                            "type": "string",
                            "visible_if": {"id_name": "b", "value": ["a", "x"]},
                        },
                        {
                            "id_name": "b",
                            "type": "menu",
                            "options": [
                                {"value": "a", "label": "A"},
                                {"value": "c", "label": "C"},
                            ],
                        },
                    ],
                }
            )

    def test_multicolumn_missing_tab_parameter(self):
        with self.assertRaisesRegex(
            ValueError, "Param 'a' has a 'tab_parameter' that is not in 'parameters'"
        ):
            validate_module_spec(
                {
                    "id_name": "id",
                    "name": "Name",
                    "category": "Clean",
                    "parameters": [
                        {
                            "id_name": "a",
                            "type": "column",
                            "tab_parameter": "b",  # does not exist
                        }
                    ],
                }
            )

    def test_multicolumn_non_tab_parameter(self):
        with self.assertRaisesRegex(
            ValueError, "Param 'a' has a 'tab_parameter' that is not a 'tab'"
        ):
            validate_module_spec(
                {
                    "id_name": "id",
                    "name": "Name",
                    "category": "Clean",
                    "parameters": [
                        {"id_name": "a", "type": "column", "tab_parameter": "b"},
                        {"id_name": "b", "type": "string"},  # Not a 'tab'
                    ],
                }
            )

    def test_multicolumn_tab_parameter(self):
        # does not raise
        validate_module_spec(
            {
                "id_name": "id",
                "name": "Name",
                "category": "Clean",
                "parameters": [
                    {"id_name": "a", "type": "column", "tab_parameter": "b"},
                    {"id_name": "b", "type": "tab"},
                ],
            }
        )

    def test_validate_menu_with_default(self):
        # does not raise
        validate_module_spec(
            {
                "id_name": "id",
                "name": "Name",
                "category": "Clean",
                "parameters": [
                    {
                        "id_name": "a",
                        "type": "menu",
                        "placeholder": "Select something",
                        "options": [
                            {"value": "x", "label": "X"},
                            "separator",
                            {"value": "y", "label": "Y"},
                            {"value": "z", "label": "Z"},
                        ],
                        "default": "y",
                    }
                ],
            }
        )

    def test_validate_menu_invalid_default(self):
        with self.assertRaisesRegex(
            ValueError, "Param 'a' has a 'default' that is not in its 'options'"
        ):
            validate_module_spec(
                {
                    "id_name": "id",
                    "name": "Name",
                    "category": "Clean",
                    "parameters": [
                        {
                            "id_name": "a",
                            "type": "menu",
                            "options": [{"value": "x", "label": "X"}],
                            "default": "y",
                        },
                        {
                            # Previously, we gave the wrong id_name
                            "id_name": "not-a",
                            "type": "string",
                        },
                    ],
                }
            )

    def test_validate_gdrivefile_missing_secret(self):
        with self.assertRaisesRegex(
            ValueError, "Param 'b' has a 'secret_parameter' that is not a 'secret'"
        ):
            validate_module_spec(
                {
                    "id_name": "id",
                    "name": "Name",
                    "category": "Clean",
                    "parameters": [
                        {"id_name": "b", "type": "gdrivefile", "secret_parameter": "a"}
                    ],
                }
            )

    def test_validate_gdrivefile_non_secret_secret(self):
        with self.assertRaisesRegex(
            ValueError, "Param 'b' has a 'secret_parameter' that is not a 'secret'"
        ):
            validate_module_spec(
                {
                    "id_name": "id",
                    "name": "Name",
                    "category": "Clean",
                    "parameters": [
                        {"id_name": "a", "type": "string"},
                        {"id_name": "b", "type": "gdrivefile", "secret_parameter": "a"},
                    ],
                }
            )

    def test_validate_gdrivefile_invalid_secret(self):
        with self.assertRaisesRegex(
            ValueError, "Param 'b' 'secret_parameter' does not refer to a 'google'"
        ):
            validate_module_spec(
                {
                    "id_name": "twitter",  # only twitter is allowed a twitter secret
                    "name": "Name",
                    "category": "Clean",
                    "parameters": [
                        {
                            "id_name": "twitter_credentials",
                            "type": "secret",
                            "secret_logic": {
                                "provider": "oauth1a",
                                "service": "twitter",
                            },
                        },
                        {
                            "id_name": "b",
                            "type": "gdrivefile",
                            "secret_parameter": "twitter_credentials",
                        },
                    ],
                }
            )

    def test_validate_allow_secret_based_on_module_id_name(self):
        validate_module_spec(
            {
                "id_name": "twitter",
                "name": "Name",
                "category": "Clean",
                "parameters": [
                    {
                        "id_name": "a",
                        "type": "secret",
                        "secret_logic": {"provider": "oauth1a", "service": "twitter"},
                    }
                ],
            }
        )

    def test_validate_disallow_secret_based_on_module_id_name(self):
        with self.assertRaisesRegex(
            ValueError, "Denied access to global 'twitter' secrets"
        ):
            validate_module_spec(
                {
                    "id_name": "eviltwitter",
                    "name": "Name",
                    "category": "Clean",
                    "parameters": [
                        {
                            "id_name": "a",
                            "type": "secret",
                            "secret_logic": {
                                "provider": "oauth1a",
                                "service": "twitter",
                            },
                        }
                    ],
                }
            )
