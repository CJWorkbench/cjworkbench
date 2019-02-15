import pathlib
import tempfile
import textwrap
from typing import Iterable, List, Tuple
import unittest
from server.models.module_loader import validate_module_spec, ModuleFiles, \
        ModuleSpec, validate_python_functions
from server.tests.utils import MockDir, MockPath


class ValidateModuleSpecTest(unittest.TestCase):
    def test_schema_errors(self):
        with self.assertRaises(ValueError) as cm:
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
        with self.assertRaisesRegex(ValueError, "Param 'dup' appears twice"):
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
        with self.assertRaises(ValueError):
            validate_module_spec({
                'id_name': 'id',
                'name': 'Name',
                'category': 'Clean',
                'parameters': [
                    {'id_name': 'menu', 'type': 'menu'},
                ],
            })

    def test_missing_radio_items(self):
        with self.assertRaises(ValueError):
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
            ValueError,
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
            ValueError,
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
            ValueError,
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


class ModuleFilesTest(unittest.TestCase):
    def test_validate_extra_json(self):
        dirpath = MockDir({
            'module.json': b'{}',
            'extra.json': b'{}',
            'module.py': b'',
        })
        with self.assertRaisesRegex(ValueError, 'Multiple.*json.*files'):
            ModuleFiles.load_from_dirpath(dirpath)

    def test_validate_extra_json_or_yaml(self):
        dirpath = MockDir({
            'module.json': b'{}',
            'extra.yaml': b'{}',
            'module.py': b'',
        })
        with self.assertRaisesRegex(ValueError, 'Multiple.*json.*files'):
            ModuleFiles.load_from_dirpath(dirpath)

    def test_validate_extra_py(self):
        dirpath = MockDir({
            'module.json': b'{}',
            'module.py': b'',
            'module2.py': b'',
        })
        with self.assertRaisesRegex(ValueError, 'Multiple.*py.*files'):
            ModuleFiles.load_from_dirpath(dirpath)

    def test_validate_missing_json(self):
        dirpath = MockDir({
            'module.py': b'',
        })
        with self.assertRaisesRegex(
            ValueError,
            'Missing ".json" or ".yaml" module-spec file'
        ):
            ModuleFiles.load_from_dirpath(dirpath)

    def test_validate_missing_py(self):
        dirpath = MockDir({
            'module.json': b'',
        })
        with self.assertRaisesRegex(ValueError,
                                    'Missing ".py" module-code file'):
            ModuleFiles.load_from_dirpath(dirpath)

    def test_ignore_setup_py(self):
        dirpath = MockDir({
            'setup.py': b'',
            'module.json': b'',
            'module.py': b'',
        })
        module_files = ModuleFiles.load_from_dirpath(dirpath)
        self.assertEqual(module_files.code.name, 'module.py')

    def test_ignore_test_py(self):
        dirpath = MockDir({
            'module.json': b'',
            'module.py': b'',
            'test_module.py': b'',
        })
        module_files = ModuleFiles.load_from_dirpath(dirpath)
        self.assertEqual(module_files.code.name, 'module.py')

    def test_ignore_package_json(self):
        dirpath = MockDir({
            'module.json': b'',
            'module.py': b'',
            'package.json': b'',
            'package-lock.json': b'',
        })
        module_files = ModuleFiles.load_from_dirpath(dirpath)
        self.assertEqual(module_files.spec.name, 'module.json')

    def test_validate_max_1_html(self):
        dirpath = MockDir({
            'module.json': b'',
            'module.py': b'',
            'module.html': b'',
            'extra.html': b'',
        })
        with self.assertRaisesRegex(ValueError, 'Multiple.*html.*files'):
            ModuleFiles.load_from_dirpath(dirpath)

    def test_validate_max_1_js(self):
        dirpath = MockDir({
            'module.json': b'',
            'module.py': b'',
            'module.js': b'',
            'extra.js': b'',
        })
        with self.assertRaisesRegex(ValueError, 'Multiple.*js.*files'):
            ModuleFiles.load_from_dirpath(dirpath)

    def test_happy_path(self):
        dirpath = MockDir({
            'module.json': b'',
            'module.py': b'',
            'module.html': b'',
            'module.js': b'',
        })
        module_files = ModuleFiles.load_from_dirpath(dirpath)
        self.assertEqual(module_files.spec.name, 'module.json')
        self.assertEqual(module_files.code.name, 'module.py')
        self.assertEqual(module_files.html.name, 'module.html')
        self.assertEqual(module_files.javascript.name, 'module.js')


class ValidatePythonFunctionsTest(unittest.TestCase):
    def _validate(self, data):
        path = MockPath(['root', 'module.py'], data)
        validate_python_functions(path)

    def test_valid_render_function(self):
        self._validate('def render(table, params):\n    return table')

    def test_valid_fetch_function(self):
        self._validate('async def fetch(params):\n    return "error"')

    def test_syntax_error(self):
        with self.assertRaises(ValueError):
            self._validate('def render(table, params')

    def test_random_error(self):
        with self.assertRaises(ValueError):
            self._validate('x()')  # NameError

    def test_missing_render_function(self):
        with self.assertRaises(ValueError):
            self._validate('def rendr(table, params):\n    return table')


class LoadModuleSpecTest(unittest.TestCase):
    def _load(self, filename, data):
        path = MockPath(['root', filename], data)
        return ModuleSpec.load_from_path(path)

    def test_load_json(self):
        spec = self._load('spec.json', b'''{
            "id_name": "foo",
            "name": "Foo",
            "category": "Clean",
            "loads_data": true,
            "parameters": [
                {"id_name": "x", "type": "string"}
            ]
        }''')
        self.assertEqual(spec.id_name, 'foo')
        self.assertEqual(spec.name, 'Foo')
        self.assertEqual(spec.category, 'Clean')
        self.assertEqual(spec['loads_data'], True)
        self.assertEqual(spec.parameters, [{'id_name': 'x', 'type': 'string'}])

    def test_json_syntax_error(self):
        with self.assertRaisesRegex(ValueError, 'JSON syntax error'):
            self._load('spec.json', b'{')

    def test_load_yaml(self):
        spec = self._load('spec.yaml', textwrap.dedent('''\
            id_name: foo
            name: Foo
            category: Clean
            loads_data: true
            parameters:
              - id_name: x
                type: string
            ''').encode('utf-8'))
        self.assertEqual(spec.id_name, 'foo')
        self.assertEqual(spec.name, 'Foo')
        self.assertEqual(spec.category, 'Clean')
        self.assertEqual(spec['loads_data'], True)
        self.assertEqual(spec.parameters, [{'id_name': 'x', 'type': 'string'}])

    def test_yaml_syntax_error(self):
        with self.assertRaisesRegex(ValueError, 'YAML syntax error'):
            self._load('spec.yaml', b'{')

    def test_dict(self):
        spec = ModuleSpec('slug', 'Name', 'Other', [], loads_data=True)
        self.assertEquals(dict(spec), {
            'id_name': 'slug',
            'name': 'Name',
            'category': 'Other',
            'parameters': [],
            'loads_data': True,
        })
