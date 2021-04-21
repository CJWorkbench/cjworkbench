import unittest
from unittest.mock import patch

from cjwkernel.pandas import module
from cjwkernel.thrift import ttypes


class MigrateParamsTests(unittest.TestCase):
    def test_default_returns_params(self):
        self.assertEqual(
            module.migrate_params_thrift({"x": ttypes.Json(string_value="y")}),
            ttypes.MigrateParamsResult({"x": ttypes.Json(string_value="y")}),
        )

    def test_allow_override(self):
        def migrate_params(params):
            self.assertEqual(params, {"x": "y"})
            return {"y": "z"}

        with patch.object(module, "migrate_params", migrate_params):
            self.assertEqual(
                module.migrate_params_thrift({"x": ttypes.Json(string_value="y")}),
                ttypes.MigrateParamsResult({"y": ttypes.Json(string_value="z")}),
            )

    def test_exception_raises(self):
        def migrate_params(params):
            raise RuntimeError("huh")

        with patch.object(module, "migrate_params", migrate_params):
            with self.assertRaisesRegex(RuntimeError, "huh"):
                module.migrate_params_thrift({})


# For render/fetch tests, look at framework.test_pandas_v0 and framework.test_arrow_v0
