import unittest
from server.models.module_version import ModuleVersion, validate_module_spec
from server.models.param_field import ParamDType
from django.core.exceptions import ValidationError
from server.tests.utils import DbTestCase


class ValidateModuleSpecTest(unittest.TestCase):
    def test_schema_errors(self):
        with self.assertRaises(ValidationError) as cm:
            validate_module_spec({
                'name': 'Hello',
                'link': 'not a link at all',
                'loads_data': 'NotABoolean',
                'parameters': []
            })

        self.assertRegex(str(cm.exception),
                         "'id_name' is a required property")
        self.assertRegex(str(cm.exception),
                         "'category' is a required property")
        self.assertRegex(str(cm.exception),
                         "'not a link at all' is not a 'uri'")
        self.assertRegex(str(cm.exception),
                         "'NotABoolean' is not of type 'boolean'")

    def test_unique_params(self):
        with self.assertRaisesRegex(
            ValidationError,
            "Param 'dup' appears twice"
        ):
            validate_module_spec({
                'id_name': 'id',
                'name': 'Name',
                'category': 'Clean',
                'parameters': [
                    {'id_name': 'dup', 'type': 'string'},
                    {'id_name': 'original', 'type': 'string'},
                    {'id_name': 'dup', 'type': 'string'},
                ],
            })

    def test_missing_menu_items(self):
        with self.assertRaises(ValidationError):
            validate_module_spec({
                'id_name': 'id',
                'name': 'Name',
                'category': 'Clean',
                'parameters': [
                    {'id_name': 'menu', 'type': 'menu'},
                ],
            })

    def test_missing_radio_items(self):
        with self.assertRaises(ValidationError):
            validate_module_spec({
                'id_name': 'id',
                'name': 'Name',
                'category': 'Clean',
                'parameters': [
                    {'id_name': 'radio', 'type': 'radio'},
                ],
            })

    def test_invalid_visible_if(self):
        with self.assertRaisesRegex(
            ValidationError,
            "Param 'a' has visible_if id_name 'b', which does not exist"
        ):
            validate_module_spec({
                'id_name': 'id',
                'name': 'Name',
                'category': 'Clean',
                'parameters': [
                    {
                        'id_name': 'a',
                        'type': 'string',
                        'visible_if': {'id_name': 'b', 'value': True},
                    },
                ],
            })

    def test_valid_visible_if(self):
        # does not raise
        validate_module_spec({
            'id_name': 'id',
            'name': 'Name',
            'category': 'Clean',
            'parameters': [
                {
                    'id_name': 'a',
                    'type': 'string',
                    'visible_if': {'id_name': 'b', 'value': True},
                },
                {
                    'id_name': 'b',
                    'type': 'string'
                }
            ],
        })

    def test_multicolumn_missing_tab_parameter(self):
        with self.assertRaisesRegex(
            ValidationError,
            "Param 'a' has a 'tab_parameter' that is not in 'parameters'"
        ):
            validate_module_spec({
                'id_name': 'id',
                'name': 'Name',
                'category': 'Clean',
                'parameters': [
                    {
                        'id_name': 'a',
                        'type': 'column',
                        'tab_parameter': 'b',  # does not exist
                    }
                ],
            })

    def test_multicolumn_non_tab_parameter(self):
        with self.assertRaisesRegex(
            ValidationError,
            "Param 'a' has a 'tab_parameter' that is not a 'tab'"
        ):
            validate_module_spec({
                'id_name': 'id',
                'name': 'Name',
                'category': 'Clean',
                'parameters': [
                    {
                        'id_name': 'a',
                        'type': 'column',
                        'tab_parameter': 'b',
                    },
                    {
                        'id_name': 'b',
                        'type': 'string',  # Not a 'tab'
                    },
                ],
            })

    def test_multicolumn_tab_parameter(self):
        # does not raise
        validate_module_spec({
            'id_name': 'id',
            'name': 'Name',
            'category': 'Clean',
            'parameters': [
                {
                    'id_name': 'a',
                    'type': 'column',
                    'tab_parameter': 'b',
                },
                {
                    'id_name': 'b',
                    'type': 'tab',
                },
            ],
        })


class ModuleVersionTest(DbTestCase):
    def test_create_module_properties(self):
        mv = ModuleVersion.create_or_replace_from_spec({
            'id_name': 'idname',
            'name': 'Name',
            'category': 'Clean',
            'link': 'http://foo.com',
            'help_url': 'a/b/c',
            'parameters': []
        }, source_version_hash='1.0')
        self.assertFalse(mv.id is None)  # it saved
        mv.refresh_from_db()
        self.assertEqual(mv.id_name, 'idname')
        self.assertEqual(mv.name, 'Name')
        self.assertEqual(mv.category, 'Clean')
        self.assertEqual(mv.help_url, 'a/b/c')

    def test_param_schema_implicit(self):
        mv = ModuleVersion.create_or_replace_from_spec({
            'id_name': 'x', 'name': 'x', 'category': 'Clean',
            'parameters': [
                {'id_name': 'foo', 'type': 'string', 'default': 'X'},
                {'id_name': 'bar', 'type': 'secret', 'name': 'Secret'},
                {'id_name': 'baz', 'type': 'menu', 'menu_items': 'a|b|c',
                 'default': 2},
            ]
        }, source_version_hash='1.0')

        self.assertEqual(repr(mv.param_schema), repr(ParamDType.Dict({
            'foo': ParamDType.String(default='X'),
            'baz': ParamDType.Enum(choices={0, 1, 2}, default=2),
        })))

    def test_param_schema_explicit(self):
        mv = ModuleVersion.create_or_replace_from_spec({
            'id_name': 'x', 'name': 'x', 'category': 'Clean',
            'parameters': [
                {'id_name': 'whee', 'type': 'custom'}
            ],
            'param_schema': {
                'id_name': {
                    'type': 'dict',
                    'properties': {
                        'x': {'type': 'integer'},
                        'y': {'type': 'string', 'default': 'X'},
                    },
                },
            },
        }, source_version_hash='1.0')

        self.assertEqual(repr(mv.param_schema), repr(ParamDType.Dict({
            'id_name': ParamDType.Dict({
                'x': ParamDType.Integer(),
                'y': ParamDType.String(default='X'),
            }),
        })))

    def test_default_params(self):
        mv = ModuleVersion.create_or_replace_from_spec({
            'id_name': 'x', 'name': 'x', 'category': 'Clean',
            'parameters': [
                {'id_name': 'foo', 'type': 'string', 'default': 'X'},
                {'id_name': 'bar', 'type': 'secret', 'name': 'Secret'},
                {'id_name': 'baz', 'type': 'menu', 'menu_items': 'a|b|c',
                 'default': 2},
            ]
        }, source_version_hash='1.0')

        self.assertEqual(mv.default_params, {'foo': 'X', 'baz': 2})

    def test_create_new_version(self):
        mv1 = ModuleVersion.create_or_replace_from_spec({
            'id_name': 'x', 'name': 'x', 'category': 'Clean', 'parameters': []
        }, source_version_hash='a')
        mv2 = ModuleVersion.create_or_replace_from_spec({
            'id_name': 'x', 'name': 'x', 'category': 'Clean', 'parameters': []
        }, source_version_hash='b')
        self.assertNotEqual(mv1.id, mv2.id)

    def test_create_new_module(self):
        mv1 = ModuleVersion.create_or_replace_from_spec({
            'id_name': 'x', 'name': 'x', 'category': 'Clean', 'parameters': []
        }, source_version_hash='a')
        mv2 = ModuleVersion.create_or_replace_from_spec({
            'id_name': 'y', 'name': 'x', 'category': 'Clean', 'parameters': []
        }, source_version_hash='a')
        self.assertNotEqual(mv1.id, mv2.id)
        # even though source_version_hash is the same

    def test_create_overwrite_version(self):
        mv1 = ModuleVersion.create_or_replace_from_spec({
            'id_name': 'x', 'name': 'x', 'category': 'Clean',
            'parameters': [{'id_name': 'x', 'type': 'string'}]
        }, source_version_hash='a')
        mv2 = ModuleVersion.create_or_replace_from_spec({
            'id_name': 'x', 'name': 'x', 'category': 'Clean', 'parameters': []
        }, source_version_hash='a')

        self.assertEqual(mv1.id, mv2.id)
