from contextlib import ExitStack  # workaround https://github.com/psf/black/issues/664
from datetime import datetime
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch
import pandas as pd
from pandas.testing import assert_frame_equal
import pyarrow as pa
from cjwkernel.tests.util import (
    arrow_table,
    arrow_table_context,
    assert_arrow_table_equals,
    assert_render_result_equals,
    parquet_file,
    override_settings,
)
from cjwkernel.util import create_tempdir, tempfile_context
from cjwkernel.thrift import ttypes
from cjwkernel.types import (
    Column,
    ColumnType,
    FetchResult,
    I18nMessage,
    Params,
    RawParams,
    RenderError,
    RenderResult,
    Tab,
    TabOutput,
    arrow_raw_params_to_thrift,
    arrow_params_to_thrift,
    arrow_arrow_table_to_thrift,
    arrow_fetch_result_to_thrift,
    arrow_tab_to_thrift,
    thrift_fetch_result_to_arrow,
    thrift_raw_params_to_arrow,
    thrift_render_result_to_arrow,
)
import cjwkernel.pandas.types as ptypes
from cjwkernel.pandas import module


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
            return [ColumnType.Text()]

        with self.assertRaisesRegex(TypeError, "not JSON serializable"):
            self._test(migrate_params)


class RenderTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.basedir = create_tempdir()

    def tearDown(self):
        shutil.rmtree(self.basedir)
        super().tearDown()

    def _test_render(
        self,
        render_fn,
        arrow_table_dict={},
        arrow_table=None,
        params={},
        tab=Tab("tab-1", "Tab 1"),
        fetch_result=None,
        output_filename=None,
    ):
        with ExitStack() as ctx:
            if arrow_table is None:
                arrow_table = ctx.enter_context(
                    arrow_table_context(arrow_table_dict, dir=self.basedir)
                )
            ctx.enter_context(patch.object(module, "render", render_fn))
            out_filename = ctx.enter_context(tempfile_context(dir=self.basedir)).name
            thrift_result = module.render_thrift(
                ttypes.RenderRequest(
                    str(self.basedir),
                    arrow_arrow_table_to_thrift(arrow_table),
                    arrow_params_to_thrift(Params(params)),
                    arrow_tab_to_thrift(tab),
                    arrow_fetch_result_to_thrift(fetch_result)
                    if fetch_result is not None
                    else None,
                    out_filename,
                )
            )
            return thrift_render_result_to_arrow(thrift_result, self.basedir)

    def test_default_render_returns_fetch_result(self):
        # Functionality used by libraryofcongress
        with ExitStack() as ctx:
            input_arrow_table = ctx.enter_context(
                arrow_table_context({"A": [1]}, dir=self.basedir)
            )
            parquet_filename = Path(
                ctx.enter_context(parquet_file({"A": [2]}, dir=self.basedir)).name
            ).name
            out_filename = ctx.enter_context(tempfile_context(dir=self.basedir)).name
            thrift_result = module.render_thrift(
                ttypes.RenderRequest(
                    str(self.basedir),
                    arrow_arrow_table_to_thrift(input_arrow_table),
                    {},  # params
                    ttypes.Tab("tab-1", "Tab 1"),
                    ttypes.FetchResult(
                        parquet_filename,
                        [
                            ttypes.RenderError(
                                ttypes.I18nMessage(
                                    "TODO_i18n",
                                    {
                                        "text": ttypes.I18nArgument(
                                            string_value="A warning"
                                        )
                                    },
                                ),
                                [],
                            )
                        ],
                    ),
                    out_filename,
                )
            )
            result = thrift_render_result_to_arrow(thrift_result, self.basedir)
            assert_render_result_equals(
                result,
                RenderResult(
                    arrow_table({"A": [2]}),
                    [RenderError(I18nMessage.TODO_i18n("A warning"))],
                ),
            )

    def test_render_with_tab_name(self):
        def render(table, params, *, tab_name):
            self.assertEqual(tab_name, "Tab X")

        self._test_render(render, tab=Tab("tab-1", "Tab X"))

    def test_render_with_no_kwargs(self):
        def render(table, params):
            return table * 2

        result = self._test_render(render, {"A": [1]})
        assert_arrow_table_equals(result.table, {"A": [2]})

    def test_render_arrow_table(self):
        # The param name "arrow_table" is a special case
        def render(arrow_table, params, output_path, **kwargs):
            out = pa.table({"A": [2]})
            with pa.ipc.RecordBatchFileWriter(output_path, out.schema) as writer:
                writer.write_table(out)

        result = self._test_render(render, {"A": [1]})
        assert_arrow_table_equals(result.table, {"A": [2]})

    def test_render_arrow_table_zero_byte_output_is_empty(self):
        # The param name "arrow_table" is a special case
        def render(arrow_table, params, output_path, **kwargs):
            output_path.write_bytes(b"")

        result = self._test_render(render, {"A": [1]})
        self.assertIsNone(result.table.path)
        self.assertIsNone(result.table.table)

    def test_render_arrow_table_missing_output_file_is_empty(self):
        # The param name "arrow_table" is a special case
        def render(arrow_table, params, output_path, **kwargs):
            try:
                output_path.unlink()
            except FileNotFoundError:
                pass

        result = self._test_render(render, {"A": [1]})
        self.assertIsNone(result.table.path)
        self.assertIsNone(result.table.table)

    def test_render_arrow_table_empty_output_table_is_empty(self):
        # The param name "arrow_table" is a special case
        def render(arrow_table, params, output_path, **kwargs):
            out = pa.table({})
            with pa.ipc.RecordBatchFileWriter(output_path, out.schema) as writer:
                writer.write_table(out)

        result = self._test_render(render, {"A": [1]})
        self.assertIsNone(result.table.path)
        self.assertIsNone(result.table.table)

    def test_render_arrow_table_errors(self):
        # The param name "arrow_table" is a special case
        def render(arrow_table, params, output_path, **kwargs):
            return [("x", {"a": "b"}, "cjwmodule")]

        result = self._test_render(render, {"A": [1]})
        self.assertEqual(
            result.errors, [RenderError(I18nMessage("x", {"a": "b"}, "cjwmodule"))]
        )

    def test_render_exception_raises(self):
        def render(table, params, **kwargs):
            raise RuntimeError("move along")

        with self.assertRaisesRegexp(RuntimeError, "move along"):
            self._test_render(render)

    def test_render_invalid_retval(self):
        def render(table, params, **kwargs):
            return {"foo": "bar"}  # not a valid retval

        with self.assertRaisesRegexp(
            ValueError, "ProcessResult input must only contain"
        ):
            self._test_render(render)

    def test_render_invalid_retval_types(self):
        def render(table, params, **kwargs):
            return pd.DataFrame({"A": [True, False]})  # we don't support bool

        with self.assertRaisesRegexp(ValueError, "unsupported dtype"):
            self._test_render(render)

    def test_render_with_parquet_fetch_result(self):
        def render(table, params, *, fetch_result):
            return fetch_result

        with parquet_file({"A": ["fetched"]}, dir=self.basedir) as pf:
            result = self._test_render(render, fetch_result=FetchResult(pf))
            assert_render_result_equals(
                result, RenderResult(arrow_table({"A": ["fetched"]}))
            )

    def test_render_with_non_parquet_fetch_result(self):
        def render(table, params, *, fetch_result):
            return pd.DataFrame({"A": [fetch_result.path.read_text()]})

        with tempfile_context(dir=self.basedir) as tf:
            tf.write_bytes(b"abcd")
            result = self._test_render(render, fetch_result=FetchResult(tf))
            assert_render_result_equals(
                result, RenderResult(arrow_table({"A": ["abcd"]}))
            )

    def test_render_empty_file_fetch_result_is_parquet(self):
        def render(table, params, *, fetch_result):
            return fetch_result.dataframe

        with tempfile_context(dir=self.basedir) as tf:
            result = self._test_render(render, fetch_result=FetchResult(tf))
            assert_render_result_equals(result, RenderResult(arrow_table({})))

    def test_render_with_input_columns(self):
        def render(table, params, *, input_columns):
            self.assertEqual(
                input_columns,
                {
                    "A": ptypes.RenderColumn("A", "text", None),
                    "B": ptypes.RenderColumn("B", "number", "{:,.3f}"),
                    "C": ptypes.RenderColumn("C", "datetime", None),
                },
            )

        with arrow_table_context(
            {"A": ["x"], "B": [1], "C": pa.array([datetime.now()], pa.timestamp("ns"))},
            columns=[
                Column("A", ColumnType.Text()),
                Column("B", ColumnType.Number("{:,.3f}")),
                Column("C", ColumnType.Datetime()),
            ],
            dir=self.basedir,
        ) as arrow_table:
            self._test_render(render, arrow_table=arrow_table)

    def test_render_use_input_columns_as_try_fallback_columns(self):
        def render(table, params, *, input_columns):
            return pd.DataFrame({"A": [1]})

        with arrow_table_context(
            {"A": [1]}, [Column("A", ColumnType.Number("{:,.3f}"))], dir=self.basedir
        ) as arrow_table:
            result = self._test_render(render, arrow_table=arrow_table)
            self.assertEqual(
                result.table.metadata.columns,
                [Column("A", ColumnType.Number("{:,.3f}"))],
            )

    def test_render_return_column_formats(self):
        def render(table, params):
            return {
                "dataframe": pd.DataFrame({"A": [1]}),
                "column_formats": {"A": "{:,d}"},
            }

        result = self._test_render(render)
        self.assertEqual(
            result.table.metadata.columns[0].type, ColumnType.Number("{:,d}")
        )

    @override_settings(MAX_ROWS_PER_TABLE=2)
    def test_render_truncate(self):
        def render(table, params):
            return pd.DataFrame({"A": [1, 2, 3]})

        result = self._test_render(render)
        assert_arrow_table_equals(result.table, {"A": [1, 2]})
        self.assertEqual(
            result.errors,
            [
                RenderError(
                    I18nMessage(
                        "py.cjwkernel.pandas.types.ProcessResult.truncate_in_place_if_too_big.warning",
                        {"old_number": 3, "new_number": 2},
                    )
                )
            ],
        )

    def test_render_using_tab_output(self):
        def render(table, params):
            self.assertEqual(params["tabparam"].slug, "tab-1")
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

        with arrow_table_context(
            {"X": [1], "Y": ["y"]},
            columns=[
                Column("X", ColumnType.Number("{:,d}")),
                Column("Y", ColumnType.Text()),
            ],
            dir=self.basedir,
        ) as atable:
            self._test_render(
                render, params={"tabparam": TabOutput(Tab("tab-1", "Tab 1"), atable)}
            )


class FetchTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.basedir = create_tempdir()

    def tearDown(self):
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
                    params=arrow_params_to_thrift(Params(params)),
                    secrets=arrow_raw_params_to_thrift(RawParams(secrets)),
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

    def test_fetch_get_stored_dataframe_happy_path(self):
        async def fetch(params, *, get_stored_dataframe):
            df = await get_stored_dataframe()
            assert_frame_equal(df, pd.DataFrame({"A": [1]}))

        with parquet_file({"A": [1]}, dir=self.basedir) as parquet_path:
            self._test_fetch(fetch, last_fetch_result=FetchResult(parquet_path, []))

    def test_fetch_get_stored_dataframe_unhandled_parquet_is_error(self):
        # Why an error? So module authors can handle it. They _created_ the
        # problem, after all. Let's help them detect it.
        async def fetch(params, *, get_stored_dataframe):
            with self.assertRaises(pa.ArrowIOError):
                await get_stored_dataframe()

        with tempfile_context(dir=self.basedir) as parquet_path:
            parquet_path.write_bytes(b"12345")
            self._test_fetch(fetch, last_fetch_result=FetchResult(parquet_path, []))

    def test_fetch_get_stored_dataframe_empty_file_is_empty_table(self):
        async def fetch(params, *, get_stored_dataframe):
            df = await get_stored_dataframe()
            assert_frame_equal(df, pd.DataFrame())

        with tempfile_context(dir=self.basedir) as parquet_path:
            self._test_fetch(fetch, last_fetch_result=FetchResult(parquet_path, []))

    def test_fetch_get_stored_dataframe_none_is_none(self):
        async def fetch(params, *, get_stored_dataframe):
            df = await get_stored_dataframe()
            self.assertIsNone(df)

        self._test_fetch(fetch, last_fetch_result=None)

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
            return pd.DataFrame({"A": [1, 2, 3]})

        with tempfile_context(dir=self.basedir) as outfile:
            result = self._test_fetch(fetch, output_filename=outfile.name)

            self.assertEqual(result.path, outfile)
            self.assertEqual(result.errors, [])
            arrow_table = pa.parquet.read_table(str(outfile), use_threads=False)
            assert_arrow_table_equals(arrow_table, {"A": [1, 2, 3]})

    def test_fetch_return_path(self):
        with tempfile_context(dir=self.basedir) as outfile:

            async def fetch(params):
                outfile.write_text("xyz")
                return outfile

            result = self._test_fetch(fetch, output_filename=outfile.name)

            self.assertEqual(result.path, outfile)
            self.assertEqual(result.errors, [])
            self.assertEqual(result.path.read_text(), "xyz")

    def test_fetch_return_tuple_path_and_error(self):
        with tempfile_context(dir=self.basedir) as outfile:

            async def fetch(params):
                outfile.write_text("xyz")
                return outfile, "foo"

            result = self._test_fetch(fetch, output_filename=outfile.name)
            self.assertEqual(result.errors, [RenderError(I18nMessage.TODO_i18n("foo"))])

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
                result,
                FetchResult(
                    outfile,
                    [RenderError(I18nMessage("message.id", {"k": "v"}, "module"))],
                ),
            )

    @override_settings(MAX_ROWS_PER_TABLE=2)
    def test_fetch_truncate(self):
        def fetch(params):
            return pd.DataFrame({"A": [1, 2, 3]})

        with tempfile_context(dir=self.basedir) as outfile:
            result = self._test_fetch(fetch, output_filename=outfile.name)
            self.assertEqual(
                result.errors,
                [
                    RenderError(
                        I18nMessage(
                            "py.cjwkernel.pandas.types.ProcessResult.truncate_in_place_if_too_big.warning",
                            {"old_number": 3, "new_number": 2},
                        )
                    )
                ],
            )
            arrow_table = pa.parquet.read_table(str(outfile), use_threads=False)
            assert_arrow_table_equals(arrow_table, {"A": [1, 2]})

    def test_fetch_return_error(self):
        async def fetch(params):
            return "bad things"

        with tempfile_context(dir=self.basedir) as outfile:
            result = self._test_fetch(fetch, output_filename=outfile.name)
            self.assertEqual(result.path, outfile)
            self.assertEqual(
                result.errors, [RenderError(I18nMessage.TODO_i18n("bad things"))]
            )
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
            result = self._test_fetch(fetch, output_filename=outfile.name)

            self.assertEqual(result.path, outfile)
            self.assertEqual(result.errors, [])
            arrow_table = pa.parquet.read_table(str(outfile), use_threads=False)
            assert_arrow_table_equals(arrow_table, {"A": [1, 2, 3]})
