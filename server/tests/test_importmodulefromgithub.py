import json
from pathlib import Path
import os
from cjwkernel.errors import ModuleCompileError
from cjwkernel.tests.util import MockDir
from cjwstate.models import ModuleVersion
from cjwstate.tests.utils import DbTestCase
from server.importmodulefromgithub import import_module_from_directory


class ImportFromGitHubTest(DbTestCase):
    def _test_module_path(self, subpath):
        """Return a subdir of ./test_data/ -- assuming it's a module."""
        return os.path.join(os.path.dirname(__file__), "test_data", subpath)

    def test_validate_invalid_spec(self):
        test_dir = self._test_module_path("bad_json_module")
        with self.assertRaises(ValueError):
            import_module_from_directory("123456", Path(test_dir))

    def test_validate_detect_python_syntax_errors(self):
        test_dir = MockDir(
            {
                "badpy.json": json.dumps(
                    dict(
                        name="Syntax-error Python",
                        id_name="badpy",
                        category="Clean",
                        parameters=[],
                    )
                ).encode("utf-8"),
                "badpy.py": b'def render(table, params):\n  cols = split(","',
            }
        )
        with self.assertRaises(ModuleCompileError):
            import_module_from_directory("123456", test_dir)

    def test_load_twice_fails(self):
        """loading the same version of the same module twice should fail"""
        test_dir = self._test_module_path("importable")
        with self.assertLogs():
            import_module_from_directory("123456", Path(test_dir))
        with self.assertRaises(ValueError):
            import_module_from_directory("123456", Path(test_dir))

    def test_load_twice_force_relaod(self):
        """We will do a reload of same version if force_reload==True"""
        test_dir = self._test_module_path("importable")
        with self.assertLogs():
            import_module_from_directory("develop", Path(test_dir))
        with self.assertLogs():
            import_module_from_directory("develop", Path(test_dir), force_reload=True)

        # should replace existing module_version, not add a new one
        self.assertEqual(ModuleVersion.objects.count(), 1)
