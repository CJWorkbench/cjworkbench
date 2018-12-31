import json
import unittest
from server.models.module_version import ModuleVersion, validate_module_spec
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
                'category': 'Cat',
                'parameters': [
                    {'id_name': 'dup', 'type': 'string'},
                    {'id_name': 'original', 'type': 'string'},
                    {'id_name': 'dup', 'type': 'string'},
                ],
            })

    def test_missing_menu_items(self):
        with self.assertRaisesRegex(
            ValidationError,
            "Param 'menu' needs menu_items"
        ):
            validate_module_spec({
                'id_name': 'id',
                'name': 'Name',
                'category': 'Cat',
                'parameters': [
                    {'id_name': 'menu', 'type': 'menu'},
                ],
            })

    def test_missing_radio_items(self):
        with self.assertRaisesRegex(
            ValidationError,
            "Param 'radio' needs radio_items"
        ):
            validate_module_spec({
                'id_name': 'id',
                'name': 'Name',
                'category': 'Cat',
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
                'category': 'Cat',
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
            'category': 'Cat',
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


class ModuleVersionTest(DbTestCase):
    def test_create_module_properties(self):
        mv = ModuleVersion.create_or_replace_from_spec({
            'id_name': 'idname',
            'name': 'Name',
            'category': 'Cat',
            'link': 'http://foo.com',
            'help_url': 'a/b/c',
            'parameters': []
        }, source_version_hash='1.0')
        self.assertFalse(mv.id is None)  # it saved
        mv.refresh_from_db()
        self.assertEqual(mv.id_name, 'idname')
        self.assertEqual(mv.name, 'Name')
        self.assertEqual(mv.category, 'Cat')
        self.assertEqual(mv.link, 'http://foo.com')
        self.assertEqual(mv.help_url, 'a/b/c')

    def test_create_parameters(self):
        mv = ModuleVersion.create_or_replace_from_spec({
            'id_name': 'x', 'name': 'x', 'category': 'x',
            'parameters': [
                {'id_name': 'foo', 'type': 'string'},
                {'id_name': 'bar', 'type': 'secret'},
            ]
        }, source_version_hash='1.0')

        self.assertEqual([(p.id_name, p.type) for p in
                          mv.parameter_specs.all()],
                         [('foo', 'string'), ('bar', 'secret')])

    def test_create_parameter_defaults(self):
        mv = ModuleVersion.create_or_replace_from_spec({
            'id_name': 'x', 'name': 'x', 'category': 'x',
            'parameters': [
                {'id_name': 'foo', 'type': 'string', 'default': 'X'},
                {'id_name': 'bar', 'type': 'secret'},
                {'id_name': 'baz', 'type': 'menu', 'menu_items': 'a|b|c',
                 'default': 2},
            ]
        }, source_version_hash='1.0')

        self.assertEqual(mv.get_default_params(), {'foo': 'X', 'baz': 2})

    def test_create_new_version(self):
        mv1 = ModuleVersion.create_or_replace_from_spec({
            'id_name': 'x', 'name': 'x', 'category': 'x', 'parameters': []
        }, source_version_hash='a')
        mv2 = ModuleVersion.create_or_replace_from_spec({
            'id_name': 'x', 'name': 'x', 'category': 'x', 'parameters': []
        }, source_version_hash='b')
        self.assertNotEqual(mv1.id, mv2.id)
        self.assertEqual(mv1.module_id, mv2.module_id)

    def test_create_new_module(self):
        mv1 = ModuleVersion.create_or_replace_from_spec({
            'id_name': 'x', 'name': 'x', 'category': 'x', 'parameters': []
        }, source_version_hash='a')
        mv2 = ModuleVersion.create_or_replace_from_spec({
            'id_name': 'y', 'name': 'x', 'category': 'x', 'parameters': []
        }, source_version_hash='a')
        self.assertNotEqual(mv1.id, mv2.id)
        self.assertNotEqual(mv1.module_id, mv2.module_id)

    def test_create_overwrite_version(self):
        mv1 = ModuleVersion.create_or_replace_from_spec({
            'id_name': 'x', 'name': 'x', 'category': 'x',
            'parameters': [{'id_name': 'x', 'type': 'string'}]
        }, source_version_hash='a')
        mv2 = ModuleVersion.create_or_replace_from_spec({
            'id_name': 'x', 'name': 'x', 'category': 'x', 'parameters': []
        }, source_version_hash='a')

        self.assertEqual(mv1.id, mv2.id)
        # Test we overwrite parameters, too
        self.assertEqual(mv1.parameter_specs.count(), 0)

    def test_create_parameter_visible_if(self):
        mv = ModuleVersion.create_or_replace_from_spec({
            'id_name': 'x', 'name': 'x', 'category': 'x',
            'parameters': [
                {'id_name': 'a', 'type': 'string'},
                {'id_name': 'b', 'type': 'string',
                 'visible_if': {'id_name': 'a', 'value': 'x'}},
            ]
        })
        pspec = list(mv.parameter_specs.all())[1]
        self.assertEqual(json.loads(pspec.visible_if),
                         {'id_name': 'a', 'value': 'x'})
