import unittest
from unittest.mock import patch

from cjwkernel.pandas import module
from cjwkernel.types import (
    RawParams,
    arrow_raw_params_to_thrift,
    thrift_raw_params_to_arrow,
)


class MigrateParamsTests(unittest.TestCase):
    def _test(self, fn, params={}):
        with patch.object(module, "migrate_params", fn):
            thrift_result = module.migrate_params_thrift(
                arrow_raw_params_to_thrift(RawParams(params))
            )
            return thrift_raw_params_to_arrow(thrift_result).params

    def test_default_returns_params(self):
        self.assertEqual(
            module.migrate_params_thrift(
                arrow_raw_params_to_thrift(RawParams({"A": [1], "B": "x"}))
            ),
            arrow_raw_params_to_thrift(RawParams({"A": [1], "B": "x"})),
        )

    def test_allow_override(self):
        def migrate_params(params):
            self.assertEqual(params, {"x": "y"})
            return {"y": "z"}

        self.assertEqual(self._test(migrate_params, {"x": "y"}), {"y": "z"})

    def test_exception_raises(self):
        def migrate_params(params):
            raise RuntimeError("huh")

        with self.assertRaisesRegex(RuntimeError, "huh"):
            self._test(migrate_params)

    def test_bad_retval_raises(self):
        def migrate_params(params):
            return [migrate_params]

        with self.assertRaisesRegex(TypeError, "not JSON serializable"):
            self._test(migrate_params)


# For render/fetch tests, look at framework.test_pandas_v0 and framework.test_arrow_v0
