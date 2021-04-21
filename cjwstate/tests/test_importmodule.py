import json
import zipfile

from cjwmodule.spec.loader import load_spec

from cjwkernel.errors import ModuleExitedError
from cjwkernel.util import tempdir_context
from cjwstate import clientside
from cjwstate.importmodule import import_zipfile, WorkbenchModuleImportError
from cjwstate.tests.utils import DbTestCaseWithModuleRegistry


class ImportModuleTest(DbTestCaseWithModuleRegistry):
    def test_validate_invalid_spec(self):
        with tempdir_context() as tempdir:
            zip_path = tempdir / "badyaml.1.zip"
            with zipfile.ZipFile(zip_path, mode="w") as zf:
                zf.writestr(
                    "badyaml.yaml",
                    (
                        b"{"
                        b'"idname": "badyaml",'
                        b'"name": "Missing id_name",'
                        b'"category": "Clean",'
                        b'"parameters": []'
                        b"}"
                    ),
                )
                zf.writestr("badyaml.py", "def render(table, params):\n  return table")
            with self.assertRaises(WorkbenchModuleImportError) as cm:
                import_zipfile(zip_path)
        self.assertIsInstance(cm.exception.__cause__, ValueError)

    def test_validate_detect_python_syntax_errors(self):
        with tempdir_context() as tempdir:
            zip_path = tempdir / "badpy.1.zip"
            with zipfile.ZipFile(zip_path, mode="w") as zf:
                zf.writestr(
                    "badpy.yaml",
                    json.dumps(
                        dict(
                            name="Syntax-error Python",
                            id_name="badpy",
                            category="Clean",
                            parameters=[],
                        )
                    ).encode("utf-8"),
                )
                zf.writestr(
                    "badpy.py", 'def render(table, params):\n  cols = split(","'
                )
            with self.assertRaises(WorkbenchModuleImportError) as cm:
                import_zipfile(zip_path)
        self.assertIsInstance(cm.exception.__cause__, SyntaxError)

    def test_validate_detect_exec_error(self):
        with tempdir_context() as tempdir:
            zip_path = tempdir / "badpy.1.zip"
            with zipfile.ZipFile(zip_path, mode="w") as zf:
                zf.writestr(
                    "badpy.yaml",
                    json.dumps(
                        dict(
                            name="Exec-error Python",
                            id_name="badpy",
                            category="Clean",
                            parameters=[],
                        )
                    ).encode("utf-8"),
                )
                zf.writestr("badpy.py", b"print(badname)")
            with self.assertRaises(WorkbenchModuleImportError) as cm:
                import_zipfile(zip_path)
        self.assertIsInstance(cm.exception.__cause__, ModuleExitedError)

    def test_happy_path(self):
        with tempdir_context() as tempdir:
            zip_path = tempdir / "importmodule.1.zip"
            with zipfile.ZipFile(zip_path, mode="w") as zf:
                zf.writestr(
                    "importmodule.yaml",
                    json.dumps(
                        dict(
                            id_name="importmodule",
                            name="Importable module",
                            category="Clean",
                            parameters=[],
                        )
                    ).encode("utf-8"),
                )
                zf.writestr(
                    "importmodule.py", b"def render(table, params): return table"
                )
            clientside_module = import_zipfile(zip_path)
        self.assertEqual(
            clientside_module,
            clientside.Module(
                spec=load_spec(
                    dict(
                        id_name="importmodule",
                        name="Importable module",
                        category="Clean",
                        parameters=[],
                    )
                ),
                js_module="",
            ),
        )
