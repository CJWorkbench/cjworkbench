from collections import namedtuple
from contextlib import ExitStack
from pathlib import Path
import unittest
from unittest.mock import patch
from cjwkernel.chroot import EDITABLE_CHROOT
from cjwkernel.errors import ModuleExitedError
from cjwkernel.param_dtype import ParamDType
from cjwkernel.types import Params, RenderResult, Tab
from cjwkernel.tests.util import (
    arrow_table,
    arrow_table_context,
    assert_render_result_equals,
)
from cjwstate import minio
from cjwstate.modules import init_module_system
from cjwstate.modules.loaded_module import LoadedModule, load_external_module
from cjwstate.tests.utils import clear_minio


MockModuleVersion = namedtuple(
    "MockModuleVersion",
    ("id_name", "source_version_hash", "param_schema", "last_update_time"),
)


class LoadedModuleTest(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        init_module_system()

    def setUp(self):
        super().setUp()

        # Clear cache _before_ the test (in case other unit tests wrote to
        # the cache -- they aren't testing the cache so they may not remember
        # to wipe it) and _after_ the unit tests (so we don't leak stuff
        # that ought to be deleted).
        load_external_module.cache_clear()
        clear_minio()

    def tearDown(self):
        load_external_module.cache_clear()
        clear_minio()

        super().tearDown()

    def test_load_static(self):
        # Test with a _real_ static module
        lm = LoadedModule.for_module_version(
            MockModuleVersion("pastecsv", "internal", ParamDType.Dict({}), "now")
        )
        self.assertEqual(lm.name, "pastecsv:internal")

    def test_load_dynamic(self):
        code = b"def render(table, params):\n    return table * 2"
        minio.client.put_object(
            Bucket=minio.ExternalModulesBucket,
            Key="imported/abcdef/imported.py",
            Body=code,
            ContentLength=len(code),
        )

        with self.assertLogs("cjwstate.modules.loaded_module"):
            lm = LoadedModule.for_module_version(
                MockModuleVersion("imported", "abcdef", ParamDType.Dict({}), "now")
            )

        self.assertEqual(lm.name, "imported:abcdef")

        # This ends up being kinda an integration test.
        with ExitStack() as ctx:
            chroot_context = ctx.enter_context(EDITABLE_CHROOT.acquire_context())
            basedir = Path(
                ctx.enter_context(
                    chroot_context.tempdir_context(prefix="test-basedir-")
                )
            )
            input_table = ctx.enter_context(
                arrow_table_context({"A": [1]}, dir=basedir)
            )
            input_table.path.chmod(0o644)
            output_path = ctx.enter_context(
                chroot_context.tempfile_context(prefix="output-", dir=basedir)
            )

            ctx.enter_context(self.assertLogs("cjwstate.modules.loaded_module"))

            result = lm.render(
                chroot_context=chroot_context,
                basedir=basedir,
                input_table=input_table,
                params=Params({"col": "A"}),
                tab=Tab("tab-1", "Tab 1"),
                fetch_result=None,
                output_filename=output_path.name,
            )

        assert_render_result_equals(result, RenderResult(arrow_table({"A": [2]})))

    def test_load_dynamic_ignore_test_py(self):
        code = b"def render(table, params):\n    return table * 2"
        minio.client.put_object(
            Bucket=minio.ExternalModulesBucket,
            Key="imported/abcdef/imported.py",
            Body=code,
            ContentLength=len(code),
        )
        # write other .py files that aren't module code and should be ignored
        minio.client.put_object(
            Bucket=minio.ExternalModulesBucket,
            Key="imported/abcdef/setup.py",
            Body=b"",
            ContentLength=0,
        )
        minio.client.put_object(
            Bucket=minio.ExternalModulesBucket,
            Key="imported/abcdef/test_imported.py",
            Body=b"",
            ContentLength=0,
        )

        with self.assertLogs("cjwstate.modules.loaded_module"):
            LoadedModule.for_module_version(
                MockModuleVersion("imported", "abcdef", ParamDType.Dict({}), "now")
            )

        # Assume we loaded the correct file -- otherwise the missing `render()`
        # would cause a verify error.

    def test_load_dynamic_is_cached(self):
        code = b"def render(table, params):\n    return table * 2"
        minio.client.put_object(
            Bucket=minio.ExternalModulesBucket,
            Key="imported/abcdef/imported.py",
            Body=code,
            ContentLength=len(code),
        )

        with self.assertLogs("cjwstate.modules.loaded_module"):
            lm = LoadedModule.for_module_version(
                MockModuleVersion("imported", "abcdef", ParamDType.Dict({}), "now")
            )

        with patch("importlib.util.module_from_spec", None):
            lm2 = LoadedModule.for_module_version(
                MockModuleVersion("imported", "abcdef", ParamDType.Dict({}), "now")
            )

        self.assertIs(lm.compiled_module, lm2.compiled_module)

    def test_load_dynamic_from_none(self):
        result = LoadedModule.for_module_version(None)
        self.assertIsNone(result)

    def test_migrate_params_retval_does_not_match_schema(self):
        # LoadedModule.migrate_params() may return invalid data: it's up to the
        # caller to validate it. In this test, we test that indeed, invalid
        # data may be returned.
        code = b"def migrate_params(params):\n    return {}"
        minio.client.put_object(
            Bucket=minio.ExternalModulesBucket,
            Key="imported/abcdef/imported.py",
            Body=code,
            ContentLength=len(code),
        )
        with self.assertLogs("cjwstate.modules.loaded_module"):
            lm = LoadedModule.for_module_version(
                MockModuleVersion(
                    "imported",
                    "abcdef",
                    ParamDType.Dict({"x": ParamDType.String()}),
                    "now",
                )
            )
            self.assertEqual(
                # should have 'x' key
                lm.migrate_params({}),
                {},
            )

    def test_migrate_params_crash(self):
        code = b"def migrate_params(params):\n    raise RuntimeError('xxx')"
        minio.client.put_object(
            Bucket=minio.ExternalModulesBucket,
            Key="imported/abcdef/imported.py",
            Body=code,
            ContentLength=len(code),
        )
        with self.assertLogs("cjwstate.modules.loaded_module"):
            lm = LoadedModule.for_module_version(
                MockModuleVersion(
                    "imported",
                    "abcdef",
                    ParamDType.Dict({"x": ParamDType.String()}),
                    "now",
                )
            )
            with self.assertRaisesRegex(ModuleExitedError, "xxx"):
                # should have 'x' key
                lm.migrate_params({})
