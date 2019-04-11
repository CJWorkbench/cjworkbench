import unittest
from server.models.module_version import ModuleVersion
from server.models.param_spec import ParamDType
from server.tests.utils import DbTestCase


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
            'baz': ParamDType.Enum(choices=frozenset({0, 1, 2}), default=2),
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
