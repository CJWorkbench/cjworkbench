import os
import shutil
import unittest
from contextlib import ExitStack  # workaround https://github.com/psf/black/issues/664
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pyarrow as pa
from cjwmodule.spec.paramschema import ParamSchema
from cjwmodule.arrow.testing import assert_arrow_table_equals, make_column, make_table
from pandas.testing import assert_frame_equal

import cjwkernel.pandas.types as ptypes
from cjwkernel.files import read_parquet_as_arrow
from cjwkernel.i18n import TODO_i18n
from cjwkernel.pandas import module
from cjwkernel.tests.util import (
    arrow_table_context,
    override_settings,
    parquet_file,
)
from cjwkernel.thrift import ttypes
from cjwkernel.types import (
    Column,
    ColumnType,
    FetchResult,
    I18nMessage,
    RenderError,
    RenderResult,
    TabOutput,
    arrow_fetch_result_to_thrift,
    pydict_to_thrift_json_object,
    thrift_fetch_result_to_arrow,
)
from cjwkernel.util import create_tempdir, tempfile_context
from .util import ModuleTestEnv


class RenderTests(unittest.TestCase):
    def test_default_render_returns_fetch_result(self):
        # Functionality used by libraryofcongress
        #
        # TODO nix this functionality.
        with ModuleTestEnv() as env:
            with parquet_file({"A": [2]}, dir=env.basedir) as parquet_path:
                outcome = env.call_render(
                    make_table(),
                    {},
                    fetch_result=FetchResult(
                        path=parquet_path, errors=[RenderError(TODO_i18n("A warning"))]
                    ),
                )
            self.assertEqual(
                outcome.result, RenderResult([RenderError(TODO_i18n("A warning"))])
            )
            assert_arrow_table_equals(
                outcome.read_table(), make_table(make_column("A", [2]))
            )

    def test_render_with_tab_name(self):
        def render(table, params, *, tab_name):
            self.assertEqual(tab_name, "Tab X")

        with ModuleTestEnv(render=render) as env:
            env.call_render(make_table(), {}, tab_name="Tab X")

    @override_settings(MAX_ROWS_PER_TABLE=12)
    def test_render_with_settings(self):
        def render(table, params, *, settings):
            self.assertEqual(settings.MAX_ROWS_PER_TABLE, 12)

        with ModuleTestEnv(render=render) as env:
            env.call_render(make_table(), {})

    def test_render_with_no_kwargs(self):
        def render(table, params):
            return table * params["n"]

        param_schema = ParamSchema.Dict({"n": ParamSchema.Float()})
        with ModuleTestEnv(param_schema=param_schema, render=render) as env:
            outcome = env.call_render(make_table(make_column("A", [1])), {"n": 2})
            assert_arrow_table_equals(
                outcome.read_table(), make_table(make_column("A", [2]))
            )

    def test_render_exception_raises(self):
        def render(table, params, **kwargs):
            raise RuntimeError("move along")

        with ModuleTestEnv(render=render) as env:
            with self.assertRaisesRegexp(RuntimeError, "move along"):
                env.call_render(make_table(), {})

    def test_render_invalid_retval(self):
        def render(table, params, **kwargs):
            return {"foo": "bar"}  # not a valid retval

        with ModuleTestEnv(render=render) as env:
            with self.assertRaisesRegexp(
                ValueError, "ProcessResult input must only contain"
            ):
                env.call_render(make_table(), {})

    def test_render_invalid_retval_types(self):
        def render(table, params, **kwargs):
            return pd.DataFrame({"A": [True, False]})  # we don't support bool

        with ModuleTestEnv(render=render) as env:
            with self.assertRaisesRegexp(ValueError, "unsupported dtype"):
                env.call_render(make_table(), {})

    def test_render_with_parquet_fetch_result(self):
        def render(table, params, *, fetch_result):
            return fetch_result

        with ModuleTestEnv(render=render) as env:
            with parquet_file({"A": ["fetched"]}, dir=env.basedir) as pf:
                outcome = env.call_render(
                    make_table(), {}, fetch_result=FetchResult(pf)
                )
                assert_arrow_table_equals(
                    outcome.read_table(), make_table(make_column("A", ["fetched"]))
                )

    def test_render_with_non_parquet_fetch_result(self):
        def render(table, params, *, fetch_result):
            return pd.DataFrame({"A": [fetch_result.path.read_text()]})

        with ModuleTestEnv(render=render) as env:
            with tempfile_context(dir=env.basedir) as tf:
                tf.write_bytes(b"abcd")
                outcome = env.call_render(
                    make_table(), {}, fetch_result=FetchResult(tf)
                )
                assert_arrow_table_equals(
                    outcome.read_table(), make_table(make_column("A", ["abcd"]))
                )

    def test_render_empty_file_fetch_result_is_parquet(self):
        def render(table, params, *, fetch_result):
            assert_frame_equal(fetch_result.dataframe, pd.DataFrame({}))
            return fetch_result.dataframe

        with ModuleTestEnv(render=render) as env:
            with tempfile_context(dir=env.basedir) as tf:
                outcome = env.call_render(
                    make_table(), {}, fetch_result=FetchResult(tf)
                )
                self.assertEqual(outcome.read_table(), make_table())

    def test_render_with_input_columns(self):
        def render(table, params, *, input_columns):
            self.assertEqual(
                input_columns,
                {
                    "A": ptypes.RenderColumn("A", "text", None),
                    "B": ptypes.RenderColumn("B", "number", "{:,.3f}"),
                    "C": ptypes.RenderColumn("C", "timestamp", None),
                    "D": ptypes.RenderColumn("D", "date", "week"),
                },
            )

        with ModuleTestEnv(render=render) as env:
            env.call_render(
                make_table(
                    make_column("A", ["x"]),
                    make_column("B", [1], format="{:,.3f}"),
                    make_column("C", [datetime.now()]),
                    make_column("D", [date(2021, 4, 12)], unit="week"),
                ),
                {},
            )

    def test_render_use_input_columns_as_try_fallback_columns(self):
        def render(table, params):
            return pd.DataFrame({"A": [2]})

        with ModuleTestEnv(render=render) as env:
            outcome = env.call_render(
                make_table(make_column("A", [1], format="{:,.3f}")), {}
            )
            self.assertEqual(
                outcome.read_table(),
                make_table(make_column("A", [2], format="{:,.3f}")),
            )

    def test_render_return_column_formats(self):
        def render(table, params):
            return {
                "dataframe": pd.DataFrame({"A": [1]}),
                "column_formats": {"A": "${:,d}"},
            }

        with ModuleTestEnv(render=render) as env:
            outcome = env.call_render(make_table(), {})
            assert_arrow_table_equals(
                outcome.read_table(), make_table(make_column("A", [1], format="${:,d}"))
            )

    @override_settings(MAX_ROWS_PER_TABLE=2)
    def test_render_truncate(self):
        def render(table, params):
            return pd.DataFrame({"A": [1, 2, 3]})

        with ModuleTestEnv(render=render) as env:
            outcome = env.call_render(make_table(), {})
            assert_arrow_table_equals(
                outcome.read_table(), make_table(make_column("A", [1, 2]))
            )
            self.assertEqual(
                outcome.result,
                RenderResult(
                    [
                        RenderError(
                            I18nMessage(
                                "py.cjwkernel.pandas.types.ProcessResult.truncate_in_place_if_too_big.warning",
                                {"old_number": 3, "new_number": 2},
                                None,
                            )
                        )
                    ]
                ),
            )

    def test_render_using_tab_output(self):
        def render(table, params):
            self.assertEqual(params["tabparam"].name, "Tab 1")
            self.assertEqual(
                params["tabparam"].columns,
                {
                    "X": ptypes.RenderColumn("X", "number", "{:,d}"),
                    "Y": ptypes.RenderColumn("Y", "text", None),
                },
            )
            assert_frame_equal(
                params["tabparam"].dataframe, pd.DataFrame({"X": [1], "Y": ["y"]})
            )

        param_schema = ParamSchema.Dict({"tabparam": ParamSchema.Tab()})
        with ModuleTestEnv(param_schema=param_schema, render=render) as env:
            with arrow_table_context(
                make_column("X", [1], format="{:,d}"),
                make_column("Y", ["y"]),
                dir=env.basedir,
            ) as (path, _):
                env.call_render(
                    make_table(),
                    params={"tabparam": "tab-1"},
                    tab_outputs={
                        "tab-1": TabOutput(tab_name="Tab 1", table_filename=path.name)
                    },
                )


class FetchTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.basedir = create_tempdir()
        self.old_cwd = os.getcwd()
        os.chdir(self.basedir)

    def tearDown(self):
        os.chdir(self.old_cwd)
        shutil.rmtree(self.basedir)
        super().tearDown()

    def _test_fetch(
        self,
        fetch_fn,
        *,
        params={},
        secrets={},
        last_fetch_result=None,
        input_table_parquet_path=None,
        output_filename=None,
    ):
        # TODO simplify this logic and move it to ModuleTestEnv
        with ExitStack() as ctx:
            ctx.enter_context(patch.object(module, "fetch", fetch_fn))
            if output_filename is None:
                # Make a temporary output filename -- this will make `fetch()`
                # complete, but callers won't be able to see the data it
                # outputs because we'll delete the file too soon.
                output_filename = ctx.enter_context(
                    tempfile_context(dir=self.basedir)
                ).name
            thrift_result = module.fetch_thrift(
                ttypes.FetchRequest(
                    basedir=str(self.basedir),
                    params=pydict_to_thrift_json_object(params),
                    secrets=pydict_to_thrift_json_object(secrets),
                    last_fetch_result=(
                        arrow_fetch_result_to_thrift(last_fetch_result)
                        if last_fetch_result is not None
                        else None
                    ),
                    input_table_parquet_filename=(
                        input_table_parquet_path.name
                        if input_table_parquet_path is not None
                        else None
                    ),
                    output_filename=output_filename,
                )
            )
            return thrift_fetch_result_to_arrow(thrift_result, self.basedir)

    def test_fetch_get_input_dataframe_happy_path(self):
        async def fetch(params, *, get_input_dataframe):
            df = await get_input_dataframe()
            assert_frame_equal(df, pd.DataFrame({"A": [1]}))

        with parquet_file({"A": [1]}, dir=self.basedir) as parquet_path:
            self._test_fetch(fetch, input_table_parquet_path=parquet_path)

    def test_fetch_get_input_dataframe_empty_file_is_empty_table(self):
        async def fetch(params, *, get_input_dataframe):
            df = await get_input_dataframe()
            assert_frame_equal(df, pd.DataFrame())

        with tempfile_context(dir=self.basedir) as input_table_parquet_path:
            self._test_fetch(fetch, input_table_parquet_path=input_table_parquet_path)

    def test_fetch_get_input_dataframe_none_is_none(self):
        async def fetch(params, *, get_input_dataframe):
            df = await get_input_dataframe()
            self.assertIsNone(df)

        self._test_fetch(fetch, input_table_parquet_path=None)

    def test_fetch_params(self):
        async def fetch(params):
            self.assertEqual(params, {"A": [{"B": "C"}]})

        self._test_fetch(fetch, params={"A": [{"B": "C"}]})

    def test_fetch_secrets(self):
        async def fetch(params, *, secrets):
            self.assertEqual(secrets, {"A": "B"})

        self._test_fetch(fetch, secrets={"A": "B"})

    def test_fetch_return_dataframe(self):
        async def fetch(params):
            return pd.DataFrame({"A": ["x", "y"]})

        with tempfile_context(dir=self.basedir) as outfile:
            result = self._test_fetch(fetch, output_filename=outfile.name)

            self.assertEqual(result.errors, [])
            arrow_table = read_parquet_as_arrow(
                outfile, [Column("A", ColumnType.Text())]
            )
            assert_arrow_table_equals(
                arrow_table, make_table(make_column("A", ["x", "y"]))
            )

    def test_fetch_return_path(self):
        with tempfile_context(dir=self.basedir) as outfile:

            async def fetch(params):
                outfile.write_text("xyz")
                return outfile

            result = self._test_fetch(fetch, output_filename=Path(outfile.name).name)

            self.assertEqual(result.path, outfile)
            self.assertEqual(result.errors, [])
            self.assertEqual(result.path.read_text(), "xyz")

    def test_fetch_return_tuple_path_and_error(self):
        with tempfile_context(dir=self.basedir) as outfile:

            async def fetch(params):
                outfile.write_text("xyz")
                return outfile, "foo"

            result = self._test_fetch(fetch, output_filename=outfile.name)
            self.assertEqual(result.errors, [RenderError(TODO_i18n("foo"))])

    def test_fetch_return_tuple_path_and_errors(self):
        with tempfile_context(dir=self.basedir) as outfile:

            async def fetch(params):
                outfile.write_text("xyz")
                return (
                    outfile,
                    [("foo", {"a": "b"}, "module"), ("bar", {"b": 1}, "cjwmodule")],
                )

            result = self._test_fetch(fetch, output_filename=outfile.name)
            self.assertEqual(
                result.errors,
                [
                    RenderError(I18nMessage("foo", {"a": "b"}, "module")),
                    RenderError(I18nMessage("bar", {"b": 1}, "cjwmodule")),
                ],
            )

    def test_fetch_return_errors(self):
        with tempfile_context(dir=self.basedir) as outfile:

            async def fetch(params):
                return [("message.id", {"k": "v"}, "module")]

            result = self._test_fetch(fetch, output_filename=outfile.name)
            self.assertEqual(
                result.errors,
                [RenderError(I18nMessage("message.id", {"k": "v"}, "module"))],
            )

    @override_settings(MAX_ROWS_PER_TABLE=2)
    def test_fetch_truncate(self):
        def fetch(params):
            return pd.DataFrame({"A": [1, 2, 3]})

        with tempfile_context(dir=self.basedir) as outfile:
            result = self._test_fetch(fetch, output_filename=outfile.name)
            self.assertEqual(
                result,
                FetchResult(
                    outfile,
                    errors=[
                        RenderError(
                            I18nMessage(
                                "py.cjwkernel.pandas.types.ProcessResult.truncate_in_place_if_too_big.warning",
                                {"old_number": 3, "new_number": 2},
                                None,
                            )
                        )
                    ],
                ),
            )
            assert_arrow_table_equals(
                read_parquet_as_arrow(
                    outfile, [Column("A", ColumnType.Number("{:,}"))]
                ),
                make_table(make_column("A", [1, 2])),
            )

    def test_fetch_return_error(self):
        async def fetch(params):
            return "bad things"

        with tempfile_context(dir=self.basedir) as outfile:
            result = self._test_fetch(fetch, output_filename=outfile.name)
            self.assertEqual(result.errors, [RenderError(TODO_i18n("bad things"))])
            self.assertEqual(outfile.read_bytes(), b"")

    def test_fetch_return_uncoerceable_dataframe_is_error(self):
        async def fetch(params):
            return pd.DataFrame({"A": [1, "2"]})  # mixed types -- invalid

        with self.assertRaisesRegex(ValueError, "invalid value"):
            self._test_fetch(fetch)

    def test_fetch_raise(self):
        async def fetch(params):
            raise RuntimeError("buggy fetch")

        with self.assertRaisesRegex(RuntimeError, "buggy fetch"):
            self._test_fetch(fetch)

    def test_fetch_sync(self):
        def fetch(params):  # not async
            return pd.DataFrame({"A": [1, 2, 3]})

        with tempfile_context(dir=self.basedir) as outfile:
            filename = Path(outfile.name).name
            result = self._test_fetch(fetch, output_filename=filename)

            self.assertEqual(result.path, outfile)
            self.assertEqual(result.errors, [])
            arrow_table = pa.parquet.read_table(str(outfile), use_threads=False)
            assert_arrow_table_equals(
                arrow_table,
                make_table(
                    make_column("A", [1, 2, 3])._replace(
                        field=pa.field(
                            "A",
                            pa.int64(),
                            metadata={"format": "{:,}", "PARQUET:field_id": "1"},
                        )
                    )
                ),
            )
