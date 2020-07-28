import unittest
from cjwstate.modules.param_dtype import ParamDType as DT
from cjwstate.modules.param_spec import ParamSpec


class ParamSpecTest(unittest.TestCase):
    maxDiff = None

    def test_checkbox_default_false(self):
        param_spec = ParamSpec.from_dict(dict(id_name="b", type="checkbox", name="hi"))
        self.assertFalse(param_spec.default)

    def test_bool_radio_default_false(self):
        # Handle odd edge case seen on production:
        #
        # If enum options are booleans and the first is True, and the _default_
        # is False, don't overwrite the default.
        param_spec = ParamSpec.from_dict(
            dict(
                id_name="r",
                type="radio",
                options=[
                    {"value": True, "label": "First"},
                    {"value": False, "label": "Second"},
                ],
                default=False,  # a valid option
            )
        )
        dtype = param_spec.dtype
        self.assertEqual(dtype.default, False)

    def test_list_dtype(self):
        # Check that ParamSpec's with List type produce correct nested DTypes
        param_spec = ParamSpec.from_dict(
            dict(
                id_name="p",
                type="list",
                child_parameters=[
                    {"id_name": "intparam", "type": "integer", "name": "my number"},
                    {"id_name": "colparam", "type": "column", "name": "my column"},
                ],
            )
        )
        self.assertEqual(
            param_spec,
            ParamSpec.List(
                id_name="p",
                child_parameters=[
                    ParamSpec.Integer(id_name="intparam", name="my number"),
                    ParamSpec.Column(id_name="colparam", name="my column"),
                ],
            ),
        )
        dtype = param_spec.dtype
        expected_dtype = DT.List(
            DT.Dict({"intparam": DT.Integer(), "colparam": DT.Column()})
        )

        # effectively do a deep compare with repr
        self.assertEqual(repr(dtype), repr(expected_dtype))

    def test_parse_menu_options(self):
        param_spec = ParamSpec.from_dict(
            dict(
                type="menu",
                id_name="id",
                name="name",
                options=[
                    {"value": True, "label": "t"},
                    "separator",
                    {"value": False, "label": "f"},
                ],
            )
        )
        self.assertEqual(
            param_spec,
            ParamSpec.Menu(
                id_name="id",
                name="name",
                default=True,  # Menu value can't be null. TODO reconsider?
                options=[
                    ParamSpec.Menu.Option.Value("t", True),
                    ParamSpec.Menu.Option.Separator,
                    ParamSpec.Menu.Option.Value("f", False),
                ],
            ),
        )

    def test_parse_radio_options(self):
        param_spec = ParamSpec.from_dict(
            dict(
                type="radio",
                id_name="id",
                name="name",
                options=[{"value": True, "label": "t"}, {"value": False, "label": "f"}],
            )
        )
        self.assertEqual(
            param_spec,
            ParamSpec.Radio(
                id_name="id",
                name="name",
                options=[
                    ParamSpec.Radio.Option("t", True),
                    ParamSpec.Radio.Option("f", False),
                ],
                default=True,
            ),
        )

    def test_to_dict_string(self):
        param_spec = ParamSpec.String(
            id_name="s", default="hi", multiline=True, syntax="python"
        )
        self.assertEqual(
            param_spec.to_dict(),
            {
                "type": "string",
                "id_name": "s",
                "name": "",
                "default": "hi",
                "multiline": True,
                "placeholder": "",
                "syntax": "python",
                "visible_if": None,
            },
        )
        # Just to make sure our unit-test is sane: verify from_dict(to_json)
        # returns the original.
        self.assertEqual(ParamSpec.from_dict(param_spec.to_dict()), param_spec)

    def test_to_dict(self):
        param_spec = ParamSpec.List(
            id_name="l",
            child_parameters=[
                ParamSpec.String(id_name="s", default="foo"),
                ParamSpec.Column(
                    id_name="c", visible_if=dict(id_name="s", value="iddqd")
                ),
            ],
        )
        param_dict = param_spec.to_dict()
        self.assertEqual(
            param_dict,
            {
                "type": "list",
                "id_name": "l",
                "name": "",
                "visible_if": None,
                "child_parameters": [
                    {
                        "type": "string",
                        "id_name": "s",
                        "name": "",
                        "default": "foo",
                        "multiline": False,
                        "placeholder": "",
                        "syntax": None,
                        "visible_if": None,
                    },
                    {
                        "type": "column",
                        "id_name": "c",
                        "placeholder": "",
                        "name": "",
                        "tab_parameter": None,
                        "column_types": None,
                        "visible_if": {"id_name": "s", "value": "iddqd"},
                    },
                ],
            },
        )
        # Just to make sure our unit-test is sane: verify from_dict(to_json)
        # returns the original.
        self.assertEqual(ParamSpec.from_dict(param_dict), param_spec)

    def test_to_dict_menu_separator(self):
        param_spec = ParamSpec.Menu(
            id_name="m",
            default="v",
            options=[
                ParamSpec.Menu.Option.Value(value="v", label="l"),
                ParamSpec.Menu.Option.Separator,
                ParamSpec.Menu.Option.Value(value="v2", label="l2"),
            ],
        )
        param_dict = param_spec.to_dict()
        self.assertEqual(
            param_dict,
            {
                "type": "menu",
                "id_name": "m",
                "default": "v",
                "placeholder": "",
                "name": "",
                "visible_if": None,
                "options": [
                    {"value": "v", "label": "l"},
                    "separator",
                    {"value": "v2", "label": "l2"},
                ],
            },
        )
        # Just to make sure our unit-test is sane: verify from_dict(to_json)
        # returns the original.
        self.assertEqual(ParamSpec.from_dict(param_dict), param_spec)

    def test_to_dict_secret_logic(self):
        param_spec = ParamSpec.Secret(
            id_name="s",
            secret_logic=dict(
                provider="string",
                label="Label",
                placeholder="Placeholder",
                help="Help",
                help_url="http://help.url",
                help_url_prompt="Help link",
            ),
        )
        param_dict = param_spec.to_dict()
        self.assertEqual(
            param_dict,
            {
                "type": "secret",
                "id_name": "s",
                "visible_if": None,
                "secret_logic": {
                    "provider": "string",
                    "label": "Label",
                    "placeholder": "Placeholder",
                    "help": "Help",
                    "help_url": "http://help.url",
                    "help_url_prompt": "Help link",
                },
            },
        )

    def test_column_column_types(self):
        param_spec = ParamSpec.from_dict(
            dict(id_name="c", type="column", column_types=["text", "number"])
        )
        self.assertEqual(param_spec.column_types, ["text", "number"])
        self.assertEqual(param_spec.dtype.column_types, frozenset(["text", "number"]))

    def test_multicolumn_column_types(self):
        param_spec = ParamSpec.from_dict(
            dict(id_name="c", type="multicolumn", column_types=["text", "number"])
        )
        self.assertEqual(param_spec.column_types, ["text", "number"])
        self.assertEqual(param_spec.dtype.column_types, frozenset(["text", "number"]))
