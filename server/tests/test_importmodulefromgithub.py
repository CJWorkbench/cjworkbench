import io
import os
import shutil
import tempfile
import pandas as pd
from server.importmodulefromgithub import validate_module_structure, \
        validate_python_functions, import_module_from_directory, \
        ValidationError
from server.models import LoadedModule, ModuleVersion, Workflow
import server.models.loaded_module
from server.modules.types import ProcessResult
from server.tests.utils import DbTestCase


class ImportFromGitHubTest(DbTestCase):
    def _test_module_path(self, subpath):
        """Return a subdir of ./test_data/ -- assuming it's a module."""
        return os.path.join(
            os.path.dirname(__file__),
            'test_data',
            subpath
        )

    def test_validate_valid_dir(self):
        test_dir = self._test_module_path('importable')
        mapping = validate_module_structure(test_dir)
        self.assertEqual(mapping, {
            'py': 'importable.py',
            'json': 'importable.json',
        })

    def test_validate_extra_json(self):
        test_dir = self._test_module_path('importable')
        with tempfile.TemporaryDirectory() as td:
            bad_dir = os.path.join(td, 'module')
            shutil.copytree(test_dir, bad_dir)
            with open(os.path.join(bad_dir, 'extra.json'), 'w'):
                pass
            with self.assertRaisesMessage(
                ValidationError,
                'Multiple files exist with extension json. '
                "This isn't currently supported"
            ):
                validate_module_structure(bad_dir)

    def test_validate_extra_py(self):
        test_dir = self._test_module_path('importable')
        with tempfile.TemporaryDirectory() as td:
            bad_dir = os.path.join(td, 'module')
            shutil.copytree(test_dir, bad_dir)
            with open(os.path.join(bad_dir, 'extra.py'), 'w'):
                pass
            with self.assertRaisesMessage(
                ValidationError,
                'Multiple files exist with extension py. '
                "This isn't currently supported"
            ):
                validate_module_structure(bad_dir)

    def test_validate_missing_json(self):
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, 'code.py'), 'w'):
                pass
            with self.assertRaisesMessage(
                ValidationError,
                'Missing ".json" module-spec file'
            ):
                validate_module_structure(td)

    def test_validate_missing_py(self):
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, 'spec.json'), 'w'):
                pass
            with self.assertRaisesMessage(
                ValidationError,
                'Missing ".py" module-code file'
            ):
                validate_module_structure(td)

    def test_ignore_setup_py(self):
        test_dir = self._test_module_path('importable')
        with tempfile.TemporaryDirectory() as td:
            good_dir = os.path.join(td, 'module')
            shutil.copytree(test_dir, good_dir)
            with open(os.path.join(good_dir, 'setup.py'), 'w'):
                pass
            validate_module_structure(good_dir)  # no error

    def test_ignore_test_py(self):
        test_dir = self._test_module_path('importable')
        with tempfile.TemporaryDirectory() as td:
            good_dir = os.path.join(td, 'module')
            shutil.copytree(test_dir, good_dir)
            with open(os.path.join(good_dir, 'test_filter.py'), 'w'):
                pass
            validate_module_structure(good_dir)  # no error

    def test_ignore_package_json(self):
        test_dir = self._test_module_path('importable')
        with tempfile.TemporaryDirectory() as td:
            good_dir = os.path.join(td, 'module')
            shutil.copytree(test_dir, good_dir)
            with open(os.path.join(good_dir, 'package.json'), 'w'):
                pass
            with open(os.path.join(good_dir, 'package-lock.json'), 'w'):
                pass
            validate_module_structure(good_dir)  # no error

    def test_validate_python_functions(self):
        test_dir = self._test_module_path('importable')
        validate_python_functions(test_dir, "importable.py")

    def test_validate_python_missing_render(self):
        # test missing/unloadable render function
        test_dir = self._test_module_path('missing_render_module')
        with self.assertRaises(ValidationError):
            validate_python_functions(test_dir, 'missing_render_module.py')

    def test_load_invalid_json(self):
        test_dir = self._test_module_path('bad_json_module')
        with self.assertRaises(ValidationError):
            import_module_from_directory('123456', test_dir)

    # syntax errors in module source files should be detected
    def test_load_invalid_python(self):
        test_dir = self._test_module_path('bad_py_module')
        with self.assertRaises(ValidationError):
            import_module_from_directory("123456", test_dir)

    # loading the same version of the same module twice should fail
    def test_load_twice(self):
        test_dir = self._test_module_path('importable')
        with self.assertLogs():
            import_module_from_directory('123456', test_dir)
        with self.assertRaises(ValidationError):
            import_module_from_directory('123456', test_dir)

    # We will do a reload of same version if force_reload==True
    def test_load_twice_force_relaod(self):
        test_dir = self._test_module_path('importable')
        with self.assertLogs():
            import_module_from_directory('develop', test_dir)
        with self.assertLogs():
            import_module_from_directory('develop', test_dir,
                                         force_reload=True)

        # should replace existing module_version, not add a new one
        self.assertEqual(ModuleVersion.objects.count(), 1)

    # THE BIG TEST. Load a module and test that we can render it correctly
    # This is really an integration test, runs both load and dispatch code
    def test_load_and_dispatch(self):
        try:
            test_dir = self._test_module_path('importable')
            with self.assertLogs():
                module_version = import_module_from_directory('123456',
                                                              test_dir)

            # Create a test workflow that uses this imported module
            workflow = Workflow.objects.create()
            tab = workflow.tabs.create(position=0)
            wfm = tab.wf_modules.create(
                order=0,
                module_id_name=module_version.id_name,
                params=module_version.default_params
            )

            # Does it render right?
            test_csv = 'Class,M,F,Other\n' \
                       'math,10,12,100\n' \
                       'english,,7,200\n' \
                       'history,11,13,\n' \
                       'economics,20,20,20'
            test_table = pd.read_csv(io.StringIO(test_csv), header=0,
                                     skipinitialspace=True)
            test_table_out = test_table.copy()
            test_table_out['M'] *= 2
            test_table_out[['F', 'Other']] *= 3

            wfm.params = {
                **wfm.params,
                'test_column': 'M',  # double this
                'test_multicolumn': 'F,Other'  # triple these
            }
            wfm.save(update_fields=['params'])

            with self.assertLogs():
                lm = LoadedModule.for_module_version_sync(module_version)
                result = lm.render(test_table, wfm.get_params(), None)
            self.assertEqual(result, ProcessResult(test_table_out))
        finally:
            server.models.loaded_module.load_external_module.cache_clear()
