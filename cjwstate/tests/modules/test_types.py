import unittest
from cjwstate.modules.types import ModuleSpec
from cjwstate.modules.param_dtype import ParamDType


class ModuleSpecTest(unittest.TestCase):
    def test_uses_data_default_true_if_loads_data_false(self):
        spec = ModuleSpec(
            id_name="id_name",
            name="Name",
            category="Add data",
            parameters=[],
            loads_data=True,
        )
        self.assertFalse(spec.get_uses_data())

    def test_uses_data_default_false_if_loads_data_true(self):
        spec = ModuleSpec(
            id_name="idname",
            name="Name",
            category="Add data",
            parameters=[],
            loads_data=False,
        )
        self.assertTrue(spec.get_uses_data())

    def test_uses_data_override(self):
        spec = ModuleSpec(
            id_name="idname",
            name="Name",
            category="Add data",
            parameters=[],
            loads_data=True,
            uses_data=True,
        )
        self.assertTrue(spec.get_uses_data())

    def test_param_schema_implicit(self):
        spec = ModuleSpec(
            id_name="googlesheets",
            name="x",
            category="Clean",
            parameters=[
                {"id_name": "foo", "type": "string", "default": "X"},
                {
                    "id_name": "bar",
                    "type": "secret",
                    "secret_logic": {"provider": "oauth2", "service": "google"},
                },
                {
                    "id_name": "baz",
                    "type": "menu",
                    "options": [
                        {"value": "a", "label": "A"},
                        "separator",
                        {"value": "c", "label": "C"},
                    ],
                    "default": "c",
                },
            ],
        )

        self.assertEqual(
            spec.get_param_schema(),
            ParamDType.Dict(
                {
                    "foo": ParamDType.String(default="X"),
                    # secret is not in param_schema
                    "baz": ParamDType.Enum(choices=frozenset({"a", "c"}), default="c"),
                }
            ),
        )

    def test_param_schema_explicit(self):
        spec = ModuleSpec(
            id_name="x",
            name="x",
            category="Clean",
            parameters=[{"id_name": "whee", "type": "custom"}],
            param_schema={
                "id_name": {
                    "type": "dict",
                    "properties": {
                        "x": {"type": "integer"},
                        "y": {"type": "string", "default": "X"},
                    },
                }
            },
        )

        self.assertEqual(
            spec.get_param_schema(),
            ParamDType.Dict(
                {
                    "id_name": ParamDType.Dict(
                        {"x": ParamDType.Integer(), "y": ParamDType.String(default="X")}
                    )
                }
            ),
        )

    def test_default_params(self):
        spec = ModuleSpec(
            id_name="x",
            name="x",
            category="Clean",
            parameters=[{"id_name": "foo", "type": "string", "default": "X"}],
        )

        self.assertEqual(spec.default_params, {"foo": "X"})
