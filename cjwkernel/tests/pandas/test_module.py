from contextlib import ExitStack  # workaround https://github.com/psf/black/issues/664
from datetime import datetime
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch
import pandas as pd
from pandas.testing import assert_frame_equal
import pyarrow
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
)
import cjwkernel.pandas.types as ptypes
from cjwkernel.pandas import module


class MigrateParamsTests(unittest.TestCase):
    def _test(self, fn, params={}):
        with patch.object(module, "migrate_params", fn):
            thrift_result = module.migrate_params_thrift(RawParams(params).to_thrift())
            return RawParams.from_thrift(thrift_result).params

    def test_default_returns_params(self):
        thrift_result = module.migrate_params_thrift(
            RawParams({"A": [1], "B": "x"}).to_thrift()
        )
        result = RawParams.from_thrift(thrift_result).params
        self.assertEqual(result, {"A": [1], "B": "x"})

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
                    arrow_table.to_thrift(),
                    Params(params).to_thrift(),
                    tab.to_thrift(),
                    fetch_result.to_thrift() if fetch_result is not None else None,
                    out_filename,
                )
            )
            return RenderResult.from_thrift(thrift_result, self.basedir)

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
                    input_arrow_table.to_thrift(),
                    Params({}).to_thrift(),
                    ttypes.Tab("tab-1", "Tab 1"),
                    ttypes.FetchResult(
                        parquet_filename,
                        [RenderError(I18nMessage.TODO_i18n("A warning")).to_thrift()],
                    ),
                    out_filename,
                )
            )
            result = RenderResult.from_thrift(thrift_result, self.basedir)
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

    def test_render_exception_raises(self):
        def render(*args, **kwargs):
            raise RuntimeError("move along")

        with self.assertRaisesRegexp(RuntimeError, "move along"):
            self._test_render(render)

    def test_render_invalid_retval(self):
        def render(*args, **kwargs):
            return {"foo": "bar"}  # not a valid retval

        with self.assertRaisesRegexp(
            ValueError, "ProcessResult input must only contain"
        ):
            self._test_render(render)

    def test_render_invalid_retval_types(self):
        def render(*args, **kwargs):
            return pd.DataFrame({"A": [True, False]})  # we don't support bool

        with self.assertRaisesRegexp(ValueError, "unsupported dtype"):
            self._test_render(render)

    def test_render_with_fetch_result(self):
        def render(*args, fetch_result):
            return fetch_result

        with parquet_file({"A": ["fetched"]}, dir=self.basedir) as pf:
            self._test_render(render, fetch_result=FetchResult(pf))
            # TODO test when fetch result is _not_ Parquet-formatted?

    def test_render_with_input_columns(self):
        def render(*args, input_columns):
            self.assertEqual(
                input_columns,
                {
                    "A": ptypes.RenderColumn("A", "text", None),
                    "B": ptypes.RenderColumn("B", "number", "{:,.3f}"),
                    "C": ptypes.RenderColumn("C", "datetime", None),
                },
            )

        with arrow_table_context(
            {"A": ["x"], "B": [1], "C": [datetime.now()]},
            columns=[
                Column("A", ColumnType.Text()),
                Column("B", ColumnType.Number("{:,.3f}")),
                Column("C", ColumnType.Datetime()),
            ],
            dir=self.basedir,
        ) as arrow_table:
            self._test_render(render, arrow_table=arrow_table)

    def test_render_use_input_columns_as_try_fallback_columns(self):
        def render(*args, input_columns):
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
        def render(*args):
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
            [RenderError(I18nMessage.TODO_i18n("Truncated output from 3 rows to 2"))],
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
                    params=Params(params).to_thrift(),
                    secrets=RawParams(secrets).to_thrift(),
                    last_fetch_result=(
                        last_fetch_result.to_thrift()
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
            return FetchResult.from_thrift(thrift_result, self.basedir)

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
            with self.assertRaises(pyarrow.ArrowIOError):
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
            arrow_table = pyarrow.parquet.read_table(str(outfile), use_threads=False)
            assert_arrow_table_equals(arrow_table, {"A": [1, 2, 3]})

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
                        I18nMessage.TODO_i18n("Truncated output from 3 rows to 2")
                    )
                ],
            )
            arrow_table = pyarrow.parquet.read_table(str(outfile), use_threads=False)
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
            arrow_table = pyarrow.parquet.read_table(str(outfile), use_threads=False)
            assert_arrow_table_equals(arrow_table, {"A": [1, 2, 3]})
