import asyncio
from collections import namedtuple
import inspect
import logging
import unittest
from unittest.mock import Mock, patch
from asgiref.sync import async_to_sync
import pandas as pd
from pandas.testing import assert_frame_equal
from cjwkernel.pandas.types import ProcessResult, Column, ColumnType
from cjwkernel.param_dtype import ParamDType
from cjwstate import minio
from cjwstate.models.loaded_module import LoadedModule, load_external_module
from cjwstate.tests.utils import clear_minio
import server.modules.pastecsv


MockModuleVersion = namedtuple(
    "MockModuleVersion",
    ("id_name", "source_version_hash", "param_schema", "last_update_time"),
)


def call_fetch(
    loaded_module,
    params,
    secrets={},
    workflow_id=1,
    input_dataframe=None,
    stored_dataframe=None,
    workflow_owner=None,
    get_input_dataframe=None,
    get_stored_dataframe=None,
):
    """
    Call loaded_module.fetch, synchronously.

    You can pass either async getters or sync values.
    """

    def wrap(retval):
        async def inner():
            return retval

        return inner

    if get_input_dataframe is None:
        get_input_dataframe = wrap(input_dataframe)

    if get_stored_dataframe is None:
        get_stored_dataframe = wrap(stored_dataframe)

    kwargs = {
        "params": params,
        "secrets": secrets,
        "workflow_id": workflow_id,
        "get_input_dataframe": get_input_dataframe,
        "get_stored_dataframe": get_stored_dataframe,
    }

    return async_to_sync(loaded_module.fetch)(**kwargs)


def async_mock(*, return_value):
    retval = asyncio.Future()
    retval.set_result(return_value)
    return Mock(return_value=retval)


class LoadedModuleTest(unittest.TestCase):
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
        lm = LoadedModule.for_module_version_sync(
            MockModuleVersion("pastecsv", "internal", ParamDType.Dict({}), "now")
        )
        self.assertEqual(lm.name, "pastecsv:internal")
        self.assertEqual(lm.render_impl, server.modules.pastecsv.render)

    def test_load_dynamic(self):
        code = b"def render(table, params):\n    return table * 2"
        minio.client.put_object(
            Bucket=minio.ExternalModulesBucket,
            Key="imported/abcdef/imported.py",
            Body=code,
            ContentLength=len(code),
        )

        with self.assertLogs("cjwstate.models.loaded_module"):
            lm = LoadedModule.for_module_version_sync(
                MockModuleVersion("imported", "abcdef", ParamDType.Dict({}), "now")
            )

        self.assertEqual(lm.name, "imported:abcdef")
        # We can't test that render_impl is exactly something, because we
        # don't have a handle on the loaded Python module outside of
        # LoadedModule. So we'll test by executing it.
        #
        # This ends up being kinda an integration test.
        with self.assertLogs("cjwstate.models.loaded_module"):
            result = lm.render(
                ProcessResult(pd.DataFrame({"A": [1, 2]})),
                {"col": "A"},
                tab_name="x",
                fetch_result=ProcessResult(),
            )
        self.assertEqual(result.error, "")
        assert_frame_equal(result.dataframe, pd.DataFrame({"A": [2, 4]}))

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

        with self.assertLogs("cjwstate.models.loaded_module"):
            lm = LoadedModule.for_module_version_sync(
                MockModuleVersion("imported", "abcdef", ParamDType.Dict({}), "now")
            )

        # We can't test that render_impl is exactly something, because we
        # don't have a handle on the loaded Python module outside of
        # LoadedModule. So we'll test by executing it.
        #
        # This ends up being kinda an integration test.
        with self.assertLogs("cjwstate.models.loaded_module"):
            result = lm.render(
                ProcessResult(pd.DataFrame({"A": [1, 2]})),
                {"col": "A"},
                tab_name="x",
                fetch_result=ProcessResult(),
            )
        self.assertEqual(result.error, "")
        assert_frame_equal(result.dataframe, pd.DataFrame({"A": [2, 4]}))

    def test_load_dynamic_is_cached(self):
        code = b"def render(table, params):\n    return table * 2"
        minio.client.put_object(
            Bucket=minio.ExternalModulesBucket,
            Key="imported/abcdef/imported.py",
            Body=code,
            ContentLength=len(code),
        )

        with self.assertLogs("cjwstate.models.loaded_module"):
            lm = LoadedModule.for_module_version_sync(
                MockModuleVersion("imported", "abcdef", ParamDType.Dict({}), "now")
            )

        with patch("importlib.util.module_from_spec", None):
            lm2 = LoadedModule.for_module_version_sync(
                MockModuleVersion("imported", "abcdef", ParamDType.Dict({}), "now")
            )

        self.assertIs(lm.render_impl, lm2.render_impl)

    def test_load_dynamic_from_none(self):
        result = LoadedModule.for_module_version_sync(None)
        self.assertIsNone(result)

    def test_render_with_fetch_result(self):
        args = None

        def render(table, params, *, fetch_result):
            nonlocal args
            args = (table, params, fetch_result)
            return pd.DataFrame({"A": [2]})

        in_table = pd.DataFrame({"A": [0]})
        params = {"foo": "bar"}
        fetch_result = ProcessResult(pd.DataFrame({"A": [1]}))
        expected = ProcessResult(pd.DataFrame({"A": [2]}))

        lm = LoadedModule("int", "1", ParamDType.Dict({}), render_impl=render)
        with self.assertLogs():
            result = lm.render(
                ProcessResult(in_table), params, tab_name="x", fetch_result=fetch_result
            )
        self.assertIs(args[0], in_table)
        self.assertIs(args[1], params)
        self.assertIs(args[2], fetch_result)
        self.assertEqual(result, expected)

    def test_render_with_input_columns(self):
        passed_columns = []

        def render(table, params, *, input_columns, **kwargs):
            nonlocal passed_columns
            passed_columns = input_columns
            return pd.DataFrame({"A": [2]})

        in_result = ProcessResult(pd.DataFrame({"A": [0]}))
        params = {"foo": "bar"}

        lm = LoadedModule("int", "1", ParamDType.Dict({}), render_impl=render)
        with self.assertLogs():
            lm.render(in_result, params, tab_name="x", fetch_result=None)

        self.assertEqual(len(passed_columns), 1)
        self.assertEqual(passed_columns["A"].name, "A")
        self.assertEqual(passed_columns["A"].type, "number")

    def test_render_with_tab_name(self):
        passed_tab_name = None

        def render(table, params, *, tab_name):
            nonlocal passed_tab_name
            passed_tab_name = tab_name

        in_result = ProcessResult(pd.DataFrame({"A": [0]}))

        lm = LoadedModule("int", "1", ParamDType.Dict({}), render_impl=render)
        with self.assertLogs():
            lm.render(in_result, {}, "Tab X", None)

        self.assertEqual(passed_tab_name, "Tab X")

    def test_render_with_no_kwargs(self):
        args = None

        def render(table, params):
            nonlocal args
            args = (table, params)
            return pd.DataFrame({"A": [1]})

        in_table = pd.DataFrame({"A": [0]})
        params = {"foo": "bar"}
        expected = ProcessResult(pd.DataFrame({"A": [1]}))

        lm = LoadedModule("int", "1", ParamDType.Dict({}), render_impl=render)
        with self.assertLogs():
            result = lm.render(
                ProcessResult(in_table), params, tab_name="x", fetch_result=None
            )
        self.assertIs(args[0], in_table)
        self.assertIs(args[1], params)
        self.assertEqual(len(args), 2)
        self.assertEqual(result, expected)

    def test_render_exception(self):
        class Ick(Exception):
            pass

        def render(table, params, **kwargs):
            raise Ick("Oops")

        lm = LoadedModule("int", "1", ParamDType.Dict({}), render_impl=render)
        with self.assertLogs(level=logging.ERROR):
            result = lm.render(ProcessResult(), {}, tab_name="x", fetch_result=None)

        _, lineno = inspect.getsourcelines(render)

        self.assertEqual(
            result,
            ProcessResult(
                error=(f"Ick: Oops at line {lineno + 1} of test_loaded_module.py")
            ),
        )

    def test_render_invalid_retval(self):
        def render(table, params):
            return pd.DataFrame({"A": [True, False]})  # we don't support bool

        lm = LoadedModule("int", "1", ParamDType.Dict({}), render_impl=render)
        with self.assertLogs(level=logging.ERROR) as cm:
            result = lm.render(ProcessResult(), {}, tab_name="x", fetch_result=None)
            # Should log an exception, which will email us
            self.assertRegex(cm.output[0], r"Exception coercing int\.render output")
            self.assertRegex(cm.output[0], r"unsupported dtype dtype\('bool'\)")
        # Should inform the user, who can follow up with the dev
        self.assertEqual(
            result,
            ProcessResult(
                error=(
                    "Something unexpected happened. We have been notified and are "
                    "working to fix it. If this persists, contact us. Error code: "
                    "unsupported dtype dtype('bool') in column 'A'"
                )
            ),
        )

    def test_render_static_default(self):
        lm = LoadedModule("int", "1", ParamDType.Dict({}))
        with self.assertLogs():
            result = lm.render(
                ProcessResult(pd.DataFrame({"A": [1]})),
                {},
                tab_name="x",
                fetch_result=None,
            )

        self.assertEqual(result, ProcessResult(pd.DataFrame({"A": [1]})))

    def test_render_truncate(self):
        calls = []

        retval = ProcessResult(pd.DataFrame({"A": [1]}))
        retval.truncate_in_place_if_too_big = lambda: calls.append("truncate")

        lm = LoadedModule(
            "int", "1", ParamDType.Dict({}), render_impl=lambda _a, _b: retval
        )
        with self.assertLogs():
            lm.render(ProcessResult(), {}, tab_name="x", fetch_result=None)
        self.assertEqual(calls, ["truncate"])

    def test_render_cannot_coerce_output(self):
        """Log and display error to user when module output is invalid."""

        def render(table, params, **kwargs):
            return {"foo": "bar"}  # not a valid retval

        lm = LoadedModule("int", "1", ParamDType.Dict({}), render_impl=render)
        with self.assertLogs(level=logging.ERROR):
            result = lm.render(ProcessResult(), {}, tab_name="x", fetch_result=None)

        _, lineno = inspect.getsourcelines(render)
        self.assertRegex(
            result.error,
            (
                "Something unexpected happened. We have been notified and are "
                "working to fix it. If this persists, contact us. Error code: "
                "ProcessResult input must only contain {dataframe, error, json, "
                "quick_fixes, column_formats}"
            ),
        )

    def test_render_use_input_columns_as_try_fallback_columns(self):
        def render(table, params):
            return pd.DataFrame({"A": [1]})

        lm = LoadedModule("int", "1", ParamDType.Dict({}), render_impl=render)
        column = Column("A", ColumnType.NUMBER("{:,d}"))
        with self.assertLogs():
            result = lm.render(
                ProcessResult(pd.DataFrame({"A": [1]}), columns=[column]),
                {},
                tab_name="x",
                fetch_result=None,
            )

        self.assertEqual(result.columns, [column])

    def test_render_format_columns(self):
        # More of an integration test....
        def render(table, params):
            return {
                "dataframe": pd.DataFrame({"A": [1]}),
                "column_formats": {"A": "{:,d}"},
            }

        lm = LoadedModule("int", "1", ParamDType.Dict({}), render_impl=render)
        with self.assertLogs():
            result = lm.render(ProcessResult(), {}, tab_name="x", fetch_result=None)

        self.assertEqual(result.columns, [Column("A", ColumnType.NUMBER("{:,d}"))])

    def test_render_invalid_return_dict_is_error(self):
        def render(table, params):
            return {"table": pd.DataFrame({"A": [1]})}  # should be 'dataframe'

        lm = LoadedModule("int", "1", ParamDType.Dict({}), render_impl=render)
        with self.assertLogs():
            result = lm.render(ProcessResult(), {}, tab_name="x", fetch_result=None)

        self.assertRegex(
            result.error,
            (
                "Something unexpected happened. We have been notified and are "
                "working to fix it. If this persists, contact us. Error code: "
                "ProcessResult input must only contain {dataframe, error, json, "
                "quick_fixes, column_formats}"
            ),
        )

    def test_render_dynamic_default(self):
        lm = LoadedModule("int", "1", ParamDType.Dict({}))
        with self.assertLogs():
            result = lm.render(
                ProcessResult(pd.DataFrame({"A": [1]})),
                {},
                tab_name="x",
                fetch_result=None,
            )

        self.assertEqual(result, ProcessResult(pd.DataFrame({"A": [1]})))

    def test_fetch_default_none(self):
        lm = LoadedModule("int", "1", ParamDType.Dict({}))
        with self.assertLogs():
            result = call_fetch(lm, {})

        self.assertIsNone(result)

    def test_fetch_secrets(self):
        async def fetch(params, *, secrets, **kwargs):
            return pd.DataFrame({"A": [repr(secrets)]})

        lm = LoadedModule("int", "1", ParamDType.Dict({}), fetch_impl=fetch)
        secret = {"name": "n", "secret": "s"}
        with self.assertLogs():
            result = call_fetch(lm, {}, {"x": secret})

        self.assertEqual(
            result, ProcessResult(pd.DataFrame({"A": [repr({"x": secret})]}))
        )

    def test_fetch_get_input_dataframe(self):
        get_input_dataframe = async_mock(return_value=pd.DataFrame({"A": [1]}))

        async def fetch(params, *, get_input_dataframe, **kwargs):
            return ProcessResult(await get_input_dataframe())

        lm = LoadedModule("int", "1", ParamDType.Dict({}), fetch_impl=fetch)
        with self.assertLogs():
            result = call_fetch(lm, {}, get_input_dataframe=get_input_dataframe)

        self.assertEqual(result, ProcessResult(pd.DataFrame({"A": [1]})))

    def test_fetch_get_stored_dataframe(self):
        get_stored_dataframe = async_mock(return_value=pd.DataFrame({"A": [1]}))

        async def fetch(params, *, get_stored_dataframe, **kwargs):
            return ProcessResult(await get_stored_dataframe())

        lm = LoadedModule("int", "1", ParamDType.Dict({}), fetch_impl=fetch)
        with self.assertLogs():
            result = call_fetch(lm, {}, get_stored_dataframe=get_stored_dataframe)

        self.assertEqual(result, ProcessResult(pd.DataFrame({"A": [1]})))

    def test_fetch_static_params(self):
        async def fetch(params, *args, **kwargs):
            # Params are a Params object
            return ProcessResult(
                pd.DataFrame({"foo": [params["foo"]], "bar": [params["bar"]]})
            )
            return ProcessResult(params.items(), columns=["key", "val"])

        lm = LoadedModule("int", "1", ParamDType.Dict({}), fetch_impl=fetch)
        with self.assertLogs():
            result = call_fetch(lm, {"foo": "bar", "bar": "baz"})

        self.assertEqual(result.error, "")
        self.assertEqual(
            result, ProcessResult(pd.DataFrame({"foo": ["bar"], "bar": ["baz"]}))
        )

    def test_fetch_sync(self):
        table = pd.DataFrame({"A": [1]})

        def fetch(params, **kwargs):
            return table

        lm = LoadedModule("int", 1, ParamDType.Dict({}), fetch_impl=fetch)
        with self.assertLogs():
            result = call_fetch(lm, {})

        self.assertEqual(result.error, "")
        assert_frame_equal(result.dataframe, table)

    def test_fetch_sync_no_params(self):
        table = pd.DataFrame({"A": [1]})

        def fetch(params):
            return table

        lm = LoadedModule("int", 1, ParamDType.Dict({}), fetch_impl=fetch)
        with self.assertLogs():
            result = call_fetch(lm, {})

        self.assertEqual(result.error, "")
        assert_frame_equal(result.dataframe, table)

    def test_fetch_dynamic_params(self):
        async def fetch(params, *args, **kwargs):
            # Params are a dict
            return ProcessResult(
                pd.DataFrame({"foo": [params["foo"]], "bar": [params["bar"]]})
            )
            return ProcessResult(params.items(), columns=["key", "val"])

        lm = LoadedModule("int", "1", ParamDType.Dict({}), fetch_impl=fetch)
        with self.assertLogs():
            result = call_fetch(lm, dict(foo="bar", bar="baz"))

        self.assertEqual(result.error, "")
        self.assertEqual(
            result, ProcessResult(pd.DataFrame({"foo": ["bar"], "bar": ["baz"]}))
        )

    def test_fetch_static_exception(self):
        class Ick(Exception):
            pass

        async def fetch(params, **kwargs):
            raise Ick("Oops")

        lm = LoadedModule("int", "1", ParamDType.Dict({}), fetch_impl=fetch)
        with self.assertLogs(level=logging.ERROR):
            result = call_fetch(lm, {})

        _, lineno = inspect.getsourcelines(fetch)
        self.assertEqual(
            result,
            ProcessResult(
                error=(f"Ick: Oops at line {lineno + 1} of test_loaded_module.py")
            ),
        )

    def test_fetch_dynamic_exception(self):
        class Ick(Exception):
            pass

        async def fetch(params, **kwargs):
            raise Ick("Oops")

        lm = LoadedModule("int", "1", ParamDType.Dict({}), fetch_impl=fetch)
        with self.assertLogs(level=logging.ERROR):
            result = call_fetch(lm, {})

        _, lineno = inspect.getsourcelines(fetch)
        self.assertEqual(
            result,
            ProcessResult(
                error=(f"Ick: Oops at line {lineno + 1} of test_loaded_module.py")
            ),
        )

    def test_fetch_invalid_retval_is_error(self):
        async def fetch(params, *, secrets, **kwargs):
            # params passed to fetch() must include secrets
            self.assertEqual(params, {"url": "http://example.org"})
            self.assertEqual(
                secrets, {"a-secret": {"name": "DO NOT LOG", "secret": "NO NO NO"}}
            )
            return pd.DataFrame({"A": [1, "2"]})  # mixed types -- invalid

        lm = LoadedModule("int", "1", ParamDType.Dict({}), fetch_impl=fetch)
        params = dict(url="http://example.org")
        secrets = {"a-secret": {"name": "DO NOT LOG", "secret": "NO NO NO"}}
        with self.assertLogs(level=logging.ERROR) as cm:
            result = call_fetch(lm, params, secrets=secrets)
            # Should log an exception, which will email us helpful debugging
            # info
            self.assertRegex(cm.output[0], r"int\.fetch gave invalid output")
            self.assertRegex(cm.output[0], r"workflow=1")
            self.assertRegex(cm.output[0], r'{"url": "http://example.org"}')
            self.assertNotRegex(cm.output[0], r"DO NOT LOG")
            self.assertRegex(cm.output[0], r"invalid value 1 in column 'A'")
        # Should inform the user, who can follow up with the dev
        self.assertEqual(
            result,
            ProcessResult(
                error=(
                    "Fetch produced invalid data: invalid value 1 in column 'A' "
                    "(object values must all be str)"
                )
            ),
        )

    def test_migrate_params_default(self):
        lm = LoadedModule(
            "x",
            "1",
            ParamDType.Dict(
                {
                    "missing": ParamDType.String(default="x"),
                    "wrong_type": ParamDType.Boolean(),
                    "ok": ParamDType.Integer(),
                }
            ),
            migrate_params_impl=None,
        )
        result = lm.migrate_params({"wrong_type": "true", "ok": 3})
        self.assertEqual(result, {"missing": "x", "wrong_type": True, "ok": 3})

    def test_migrate_params_impl(self):
        def migrate_params(params):
            return {"x": params["a"], "y": params["b"]}

        lm = LoadedModule(
            "x",
            "1",
            ParamDType.Dict({"x": ParamDType.Integer(), "y": ParamDType.Integer()}),
            migrate_params_impl=migrate_params,
        )
        result = lm.migrate_params({"a": 1, "b": 2})
        self.assertEqual(result, {"x": 1, "y": 2})

    def test_migrate_params_impl_exception(self):
        def migrate_params(params):
            {}["a"]

        lm = LoadedModule(
            "x", "1", ParamDType.Dict({}), migrate_params_impl=migrate_params
        )
        with self.assertRaisesRegex(ValueError, r"migrate_params\(\) raised KeyError"):
            lm.migrate_params({})

    def test_migrate_params_impl_missing_output(self):
        lm = LoadedModule(
            "x",
            "1",
            ParamDType.Dict({"x": ParamDType.String()}),
            migrate_params_impl=lambda x: x,
        )
        with self.assertRaises(ValueError):
            # should have 'x' key
            lm.migrate_params({})

    def test_migrate_params_impl_wrong_output_type(self):
        lm = LoadedModule(
            "x",
            "1",
            ParamDType.Dict({"x": ParamDType.String()}),
            migrate_params_impl=lambda x: x,
        )
        with self.assertRaises(ValueError):
            # should be str
            lm.migrate_params({"x": 2})

    def test_migrate_params_impl_extra_output(self):
        lm = LoadedModule(
            "x", "1", ParamDType.Dict({}), migrate_params_impl=lambda x: x
        )
        with self.assertRaises(ValueError):
            lm.migrate_params({"x": "should not be here"})
