import io
import json
import time
import zipfile
from cjwkernel.errors import ModuleExitedError
from cjwstate import minio
from cjwstate.models.module_registry import MODULE_REGISTRY
from cjwstate.models.module_version import ModuleVersion
from cjwstate.modules import init_module_system
from cjwstate.modules.types import ModuleSpec
from cjwstate.tests.utils import DbTestCase


class ModuleRegistryTest(DbTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        init_module_system()
        minio.ensure_bucket_exists(minio.StaticFilesBucket)

    # All the keys written to minio in this test are different. That's so that
    # minio's output will be consistent read-after-write. If we were to delete
    # and then overwrite a key, minio's output would be _eventually_
    # consistent -- which means one test could read a file another test wrote.

    def test_latest_internal(self):
        zf = MODULE_REGISTRY.latest("pythoncode")
        self.assertEqual(zf.get_spec().id_name, "pythoncode")

    def test_all_latest_internal(self):
        zf = MODULE_REGISTRY.all_latest()["pythoncode"]
        self.assertEqual(zf.get_spec().id_name, "pythoncode")

    def test_db_minio_latest_order_by_last_update_time(self):
        # old version
        ModuleVersion.create_or_replace_from_spec(
            {
                "id_name": "regtest1",
                "name": "regtest1 v1",
                "category": "Clean",
                "parameters": [{"id_name": "url", "type": "string"}],
            },
            source_version_hash="b1c2d3",
        )
        time.sleep(0.000002)  # guarantee new timestamp
        # new version
        v2 = ModuleVersion.create_or_replace_from_spec(
            {
                "id_name": "regtest1",
                "name": "regtest1 v2",
                "category": "Clean",
                "parameters": [{"id_name": "url", "type": "string"}],
            },
            source_version_hash="b1c2d2",
        )
        bio = io.BytesIO()
        with zipfile.ZipFile(bio, mode="w") as zf:
            zf.writestr("regtest1.yaml", json.dumps(v2.spec).encode("utf-8"))
            zf.writestr("regtest1.py", b"def render(table, params):\n    return table")
        minio.put_bytes(
            minio.ExternalModulesBucket,
            "regtest1/regtest1.b1c2d2.zip",
            bytes(bio.getbuffer()),
        )

        zf = MODULE_REGISTRY.latest("regtest1")
        self.assertEqual(zf.get_spec(), ModuleSpec(**v2.spec))

    def test_db_minio_latest_load_deprecated_simple(self):
        mv = ModuleVersion.create_or_replace_from_spec(
            {
                "id_name": "regtest2",
                "name": "regtest2 v1",
                "category": "Clean",
                "parameters": [{"id_name": "url", "type": "string"}],
            },
            source_version_hash="b1c2d2",
        )
        minio.put_bytes(
            minio.ExternalModulesBucket,
            "regtest2/b1c2d2/regtest2.py",
            "def render(table, params):\n    return table",
        )
        minio.put_bytes(
            minio.ExternalModulesBucket,
            "regtest2/b1c2d2/regtest2.yaml",
            json.dumps(mv.spec).encode("utf-8"),
        )

        zf = MODULE_REGISTRY.latest("regtest2")
        self.assertEqual(zf.get_spec(), ModuleSpec(**mv.spec))
        self.assertIsNone(zf.get_optional_html())

    def test_db_minio_latest_load_deprecated_html(self):
        mv = ModuleVersion.create_or_replace_from_spec(
            {
                "id_name": "regtest3",
                "name": "regtest3 v2",
                "category": "Clean",
                "parameters": [{"id_name": "url", "type": "string"}],
            },
            source_version_hash="b1c2d2",
        )
        minio.put_bytes(
            minio.ExternalModulesBucket,
            "regtest3/b1c2d2/regtest3.py",
            "def render(table, params):\n    return table",
        )
        minio.put_bytes(
            minio.ExternalModulesBucket,
            "regtest3/b1c2d2/regtest3.yaml",
            json.dumps(mv.spec).encode("utf-8"),
        )
        html = "<!DOCTYPE html><html><head><title>Hi</title></head><body>Hello, world!</body></html>"
        minio.put_bytes(
            minio.ExternalModulesBucket,
            "regtest3/b1c2d2/regtest3.html",
            html.encode("utf-8"),
        )

        zf = MODULE_REGISTRY.latest("regtest3")
        self.assertEqual(zf.get_optional_html(), html)

    def test_db_minio_use_cache_for_same_version(self):
        mv = ModuleVersion.create_or_replace_from_spec(
            {
                "id_name": "regtest4",
                "name": "regtest4 v1",
                "category": "Clean",
                "parameters": [{"id_name": "url", "type": "string"}],
            },
            source_version_hash="b1c2d2",
        )
        bio = io.BytesIO()
        with zipfile.ZipFile(bio, mode="w") as zf:
            zf.writestr("regtest4.yaml", json.dumps(mv.spec).encode("utf-8"))
            zf.writestr("regtest4.py", b"def render(table, params):\n    return table")
        minio.put_bytes(
            minio.ExternalModulesBucket,
            "regtest4/regtest4.b1c2d2.zip",
            bytes(bio.getbuffer()),
        )

        zf1 = MODULE_REGISTRY.latest("regtest4")
        zf2 = MODULE_REGISTRY.latest("regtest4")
        self.assertIs(zf2, zf1)

    def test_db_minio_refresh_cache_for_new_version(self):
        v1 = ModuleVersion.create_or_replace_from_spec(
            {
                "id_name": "regtest5",
                "name": "regtest5 v1",
                "category": "Clean",
                "parameters": [{"id_name": "url", "type": "string"}],
            },
            source_version_hash="b1c2d2",
        )
        bio = io.BytesIO()
        with zipfile.ZipFile(bio, mode="w") as zf:
            zf.writestr("regtest5.yaml", json.dumps(v1.spec).encode("utf-8"))
            zf.writestr("regtest5.py", b"def render(table, params):\n    return table")
        minio.put_bytes(
            minio.ExternalModulesBucket,
            "regtest5/regtest5.b1c2d2.zip",
            bytes(bio.getbuffer()),
        )

        zipfile1 = MODULE_REGISTRY.latest("regtest5")

        ModuleVersion.create_or_replace_from_spec(
            {
                "id_name": "regtest5",
                "name": "regtest5 v2",
                "category": "Clean",
                "parameters": [{"id_name": "url", "type": "string"}],
            },
            source_version_hash="b1c2d3",
        )
        minio.put_bytes(
            minio.ExternalModulesBucket,
            "regtest5/regtest5.b1c2d3.zip",
            bytes(bio.getbuffer()),  # reuse zipfile to save lines of code
        )

        zipfile2 = MODULE_REGISTRY.latest("regtest5")

        self.assertIsNot(zipfile2, zipfile1)
        self.assertEqual(zipfile2.version, "b1c2d3")

    def test_db_minio_syntax_error_is_runtime_error(self):
        mv = ModuleVersion.create_or_replace_from_spec(
            {
                "id_name": "regtest9",
                "name": "regtest9 v1",
                "category": "Clean",
                "parameters": [{"id_name": "url", "type": "string"}],
            },
            source_version_hash="b1c2d3",
        )
        bio = io.BytesIO()
        with zipfile.ZipFile(bio, mode="w") as zf:
            zf.writestr(
                "regtest9.yaml",
                json.dumps({**mv.spec, "parameters": "not an Array"}).encode("utf-8"),
            )
            zf.writestr("regtest9.py", b"def render(")
        minio.put_bytes(
            minio.ExternalModulesBucket,
            "regtest9/regtest9.b1c2d3.zip",
            bytes(bio.getbuffer()),
        )

        with self.assertRaises(RuntimeError) as cm:
            MODULE_REGISTRY.latest("regtest9")
        self.assertIsInstance(cm.exception.__cause__, SyntaxError)

    def test_db_minio_validate_spec(self):
        mv = ModuleVersion.create_or_replace_from_spec(
            {
                "id_name": "regtest8",
                "name": "regtest8 v1",
                "category": "Clean",
                "parameters": [{"id_name": "url", "type": "string"}],
            },
            source_version_hash="b1c2d3",
        )
        bio = io.BytesIO()
        with zipfile.ZipFile(bio, mode="w") as zf:
            zf.writestr(
                "regtest8.yaml",
                json.dumps({**mv.spec, "parameters": "not an Array"}).encode("utf-8"),
            )
            zf.writestr("regtest8.py", b"def render(table, params):\n    return table")
        minio.put_bytes(
            minio.ExternalModulesBucket,
            "regtest8/regtest8.b1c2d3.zip",
            bytes(bio.getbuffer()),
        )

        with self.assertRaises(RuntimeError) as cm:
            MODULE_REGISTRY.latest("regtest8")
        self.assertIsInstance(cm.exception.__cause__, ValueError)

    def test_db_minio_validate_code_with_kernel(self):
        mv = ModuleVersion.create_or_replace_from_spec(
            {
                "id_name": "regtest7",
                "name": "regtest7 v1",
                "category": "Clean",
                "parameters": [{"id_name": "url", "type": "string"}],
            },
            source_version_hash="b1c2d3",
        )
        bio = io.BytesIO()
        with zipfile.ZipFile(bio, mode="w") as zf:
            zf.writestr("regtest7.yaml", json.dumps(mv.spec).encode("utf-8"))
            zf.writestr(
                "regtest7.py", b"def render(table, params):\n    return table\nfoo()"
            )
        minio.put_bytes(
            minio.ExternalModulesBucket,
            "regtest7/regtest7.b1c2d3.zip",
            bytes(bio.getbuffer()),
        )

        with self.assertRaises(RuntimeError) as cm:
            MODULE_REGISTRY.latest("regtest7")
        self.assertIsInstance(cm.exception.__cause__, ModuleExitedError)

    def test_db_minio_all_latest_use_max_last_update_time(self):
        # old version
        ModuleVersion.create_or_replace_from_spec(
            {
                "id_name": "regtest6",
                "name": "regtest6 v1",
                "category": "Clean",
                "parameters": [{"id_name": "url", "type": "string"}],
            },
            source_version_hash="b1c2d3",
        )
        time.sleep(0.000002)  # guarantee new timestamp
        # new version
        v2 = ModuleVersion.create_or_replace_from_spec(
            {
                "id_name": "regtest6",
                "name": "regtest6 v2",
                "category": "Clean",
                "parameters": [{"id_name": "url", "type": "string"}],
            },
            source_version_hash="b1c2d2",
        )
        bio = io.BytesIO()
        with zipfile.ZipFile(bio, mode="w") as zf:
            zf.writestr("regtest6.yaml", json.dumps(v2.spec).encode("utf-8"))
            zf.writestr("regtest6.py", b"def render(table, params):\n    return table")
        minio.put_bytes(
            minio.ExternalModulesBucket,
            "regtest6/regtest6.b1c2d2.zip",
            bytes(bio.getbuffer()),
        )

        zf = MODULE_REGISTRY.all_latest()["regtest6"]
        self.assertEqual(zf.get_spec(), ModuleSpec(**v2.spec))
