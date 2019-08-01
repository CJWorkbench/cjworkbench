import io
import json
from pathlib import Path
import os
import shutil
import tempfile
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from cjworkbench.types import ProcessResult
from server.importmodulefromgithub import import_module_from_directory
from server.models import LoadedModule, ModuleVersion, Workflow
from server.models.module_loader import validate_python_functions
import server.models.loaded_module
from server.tests.utils import DbTestCase, MockDir, MockPath


class ImportFromGitHubTest(DbTestCase):
    def _test_module_path(self, subpath):
        """Return a subdir of ./test_data/ -- assuming it's a module."""
        return os.path.join(os.path.dirname(__file__), "test_data", subpath)

    def test_validate_valid_python_functions(self):
        test_dir = Path(self._test_module_path("importable"))
        validate_python_functions(test_dir / "importable.py")

    def test_validate_python_missing_render(self):
        """test missing/unloadable render function"""
        test_dir = Path(self._test_module_path("missing_render_module"))
        with self.assertRaisesRegex(ValueError, "missing_render_module.py"):
            validate_python_functions(test_dir / "missing_render_module.py")

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
        with self.assertRaises(ValueError):
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

    # THE BIG TEST. Load a module and test that we can render it correctly
    # This is really an integration test, runs both load and dispatch code
    def test_load_and_dispatch(self):
        try:
            test_dir = self._test_module_path("importable")
            with self.assertLogs():
                module_version = import_module_from_directory("123456", Path(test_dir))

            # Create a test workflow that uses this imported module
            workflow = Workflow.objects.create()
            tab = workflow.tabs.create(position=0)
            wfm = tab.wf_modules.create(
                order=0,
                slug="step-1",
                module_id_name=module_version.id_name,
                params={
                    **module_version.default_params,
                    "test_column": "M",  # double this
                    "test_multicolumn": ["F", "Other"],  # triple these
                },
            )

            # Does it render right?
            test_table = pd.DataFrame(
                {
                    "Class": ["math", "english", "history", "economics"],
                    "M": [10, np.nan, 11, 20],
                    "F": [12, 7, 13, 20],
                    "Other": [100, 100, 13, 20],
                }
            )
            expected = pd.DataFrame(
                {
                    "Class": ["math", "english", "history", "economics"],
                    "M": [20, np.nan, 22, 40],
                    "F": [36, 21, 39, 60],
                    "Other": [300, 300, 39, 60],
                }
            )

            with self.assertLogs():
                lm = LoadedModule.for_module_version_sync(module_version)
                result = lm.render(
                    ProcessResult(test_table), wfm.get_params(), "x", None
                )
            self.assertEqual(result.error, "")
            assert_frame_equal(result.dataframe, expected)
        finally:
            server.models.loaded_module.load_external_module.cache_clear()
