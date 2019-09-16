from contextlib import ExitStack  # workaround https://github.com/psf/black/issues/664
from datetime import datetime
from pathlib import Path
import tempfile
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
                arrow_table = ctx.enter_context(arrow_table_context(arrow_table_dict))
            ctx.enter_context(patch.object(module, "render", render_fn))
            out_filename = ctx.enter_context(tempfile.NamedTemporaryFile()).name
            thrift_result = module.render_thrift(
                ttypes.RenderRequest(
                    arrow_table.to_thrift(),
                    Params(params).to_thrift(),
                    tab.to_thrift(),
                    fetch_result.to_thrift() if fetch_result is not None else None,
                    out_filename,
                )
            )
            return RenderResult.from_thrift(thrift_result)

    def test_default_render_returns_fetch_result(self):
        # Functionality used by libraryofcongress
        with ExitStack() as ctx:
            input_arrow_table = ctx.enter_context(arrow_table_context({"A": [1]}))
            parquet_path = ctx.enter_context(parquet_file({"A": [2]}))
            out_filename = ctx.enter_context(tempfile.NamedTemporaryFile()).name
            thrift_result = module.render_thrift(
                ttypes.RenderRequest(
                    input_arrow_table.to_thrift(),
                    Params({}).to_thrift(),
                    ttypes.Tab("tab-1", "Tab 1"),
                    FetchResult(
                        parquet_path, [RenderError(I18nMessage.TODO_i18n("A warning"))]
                    ).to_thrift(),
                    out_filename,
                )
            )
            result = RenderResult.from_thrift(thrift_result)
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

        with parquet_file({"A": ["fetched"]}) as pf:
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
        ) as arrow_table:
            self._test_render(render, arrow_table=arrow_table)

    def test_render_use_input_columns_as_try_fallback_columns(self):
        def render(*args, input_columns):
            return pd.DataFrame({"A": [1]})

        with arrow_table_context(
            {"A": [1]}, [Column("A", ColumnType.Number("{:,.3f}"))]
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


class FetchTests(unittest.TestCase):
    def test_fetch_get_stored_dataframe_happy_path(self):
        async def fetch(params, *, get_stored_dataframe):
            df = await get_stored_dataframe()
            assert_frame_equal(df, pd.DataFrame({"A": [1]}))

        with ExitStack() as ctx:
            output_filename = ctx.enter_context(tempfile.NamedTemporaryFile()).name
            stored_filename = ctx.enter_context(parquet_file({"A": [1]}))
            ctx.enter_context(patch.object(module, "fetch", fetch))
            module.fetch_thrift(
                ttypes.FetchRequest(
                    params=Params({}).to_thrift(),
                    secrets=RawParams({}).to_thrift(),
                    last_fetch_result=ttypes.FetchResult(stored_filename, []),
                    output_filename=output_filename,
                )
            )

    def test_fetch_get_stored_dataframe_unhandled_parquet_is_error(self):
        # Why an error? So module authors can handle it. They _created_ the
        # problem, after all. Let's help them detect it.
        async def fetch(params, *, get_stored_dataframe):
            with self.assertRaises(pyarrow.ArrowIOError):
                await get_stored_dataframe()

        with ExitStack() as ctx:
            output_filename = ctx.enter_context(tempfile.NamedTemporaryFile()).name
            stored_filename = ctx.enter_context(tempfile.NamedTemporaryFile()).name
            ctx.enter_context(patch.object(module, "fetch", fetch))
            Path(stored_filename).write_bytes(b"12345")
            module.fetch_thrift(
                ttypes.FetchRequest(
                    params=Params({}).to_thrift(),
                    secrets=RawParams({}).to_thrift(),
                    last_fetch_result=ttypes.FetchResult(stored_filename, []),
                    output_filename=output_filename,
                )
            )

    def test_fetch_get_stored_dataframe_empty_file_is_empty_table(self):
        async def fetch(params, *, get_stored_dataframe):
            df = await get_stored_dataframe()
            assert_frame_equal(df, pd.DataFrame())

        with ExitStack() as ctx:
            output_filename = ctx.enter_context(tempfile.NamedTemporaryFile()).name
            stored_filename = ctx.enter_context(tempfile.NamedTemporaryFile()).name
            ctx.enter_context(patch.object(module, "fetch", fetch))
            module.fetch_thrift(
                ttypes.FetchRequest(
                    params=Params({}).to_thrift(),
                    secrets=RawParams({}).to_thrift(),
                    last_fetch_result=ttypes.FetchResult(stored_filename, []),
                    output_filename=output_filename,
                )
            )

    def test_fetch_get_stored_dataframe_none_is_none(self):
        async def fetch(params, *, get_stored_dataframe):
            df = await get_stored_dataframe()
            self.assertIsNone(df)

        with ExitStack() as ctx:
            output_filename = ctx.enter_context(tempfile.NamedTemporaryFile()).name
            ctx.enter_context(patch.object(module, "fetch", fetch))
            module.fetch_thrift(
                ttypes.FetchRequest(
                    params=Params({}).to_thrift(),
                    secrets=RawParams({}).to_thrift(),
                    output_filename=output_filename,
                )
            )

    def test_fetch_get_input_dataframe_happy_path(self):
        async def fetch(params, *, get_input_dataframe):
            df = await get_input_dataframe()
            assert_frame_equal(df, pd.DataFrame({"A": [1]}))

        with ExitStack() as ctx:
            output_filename = ctx.enter_context(tempfile.NamedTemporaryFile()).name
            input_filename = ctx.enter_context(parquet_file({"A": [1]}))
            ctx.enter_context(patch.object(module, "fetch", fetch))
            module.fetch_thrift(
                ttypes.FetchRequest(
                    params=Params({}).to_thrift(),
                    secrets=RawParams({}).to_thrift(),
                    input_table_parquet_filename=input_filename,
                    output_filename=output_filename,
                )
            )

    def test_fetch_get_input_dataframe_empty_file_is_empty_table(self):
        async def fetch(params, *, get_input_dataframe):
            df = await get_input_dataframe()
            assert_frame_equal(df, pd.DataFrame())

        with ExitStack() as ctx:
            output_filename = ctx.enter_context(tempfile.NamedTemporaryFile()).name
            input_filename = ctx.enter_context(tempfile.NamedTemporaryFile()).name
            ctx.enter_context(patch.object(module, "fetch", fetch))
            module.fetch_thrift(
                ttypes.FetchRequest(
                    params=Params({}).to_thrift(),
                    secrets=RawParams({}).to_thrift(),
                    input_table_parquet_filename=input_filename,
                    output_filename=output_filename,
                )
            )

    def test_fetch_get_input_dataframe_none_is_none(self):
        async def fetch(params, *, get_input_dataframe):
            df = await get_input_dataframe()
            self.assertIsNone(df)

        with ExitStack() as ctx:
            output_filename = ctx.enter_context(tempfile.NamedTemporaryFile()).name
            ctx.enter_context(patch.object(module, "fetch", fetch))
            module.fetch_thrift(
                ttypes.FetchRequest(
                    params=Params({}).to_thrift(),
                    secrets=RawParams({}).to_thrift(),
                    output_filename=output_filename,
                )
            )

    def test_fetch_params(self):
        async def fetch(params):
            self.assertEqual(params, {"A": [{"B": "C"}]})

        with ExitStack() as ctx:
            output_filename = ctx.enter_context(tempfile.NamedTemporaryFile()).name
            ctx.enter_context(patch.object(module, "fetch", fetch))
            module.fetch_thrift(
                ttypes.FetchRequest(
                    params=Params({"A": [{"B": "C"}]}).to_thrift(),
                    secrets=RawParams({}).to_thrift(),
                    output_filename=output_filename,
                )
            )

    def test_fetch_secrets(self):
        async def fetch(params, *, secrets):
            self.assertEqual(secrets, {"A": "B"})

        with ExitStack() as ctx:
            output_filename = ctx.enter_context(tempfile.NamedTemporaryFile()).name
            ctx.enter_context(patch.object(module, "fetch", fetch))
            module.fetch_thrift(
                ttypes.FetchRequest(
                    params=Params({}).to_thrift(),
                    secrets=RawParams({"A": "B"}).to_thrift(),
                    output_filename=output_filename,
                )
            )

    def test_fetch_return_dataframe(self):
        async def fetch(params):
            return pd.DataFrame({"A": [1, 2, 3]})

        with ExitStack() as ctx:
            output_filename = ctx.enter_context(tempfile.NamedTemporaryFile()).name
            ctx.enter_context(patch.object(module, "fetch", fetch))
            result = module.fetch_thrift(
                ttypes.FetchRequest(
                    params=Params({}).to_thrift(),
                    secrets=RawParams({}).to_thrift(),
                    output_filename=output_filename,
                )
            )
            self.assertEqual(result.filename, output_filename)
            self.assertEqual(result.errors, [])
            arrow_table = pyarrow.parquet.read_table(output_filename, use_threads=False)
            assert_arrow_table_equals(arrow_table, {"A": [1, 2, 3]})

    def test_fetch_return_error(self):
        async def fetch(params):
            return "bad things"

        with ExitStack() as ctx:
            output_filename = ctx.enter_context(tempfile.NamedTemporaryFile()).name
            ctx.enter_context(patch.object(module, "fetch", fetch))
            result = module.fetch_thrift(
                ttypes.FetchRequest(
                    params=Params({}).to_thrift(),
                    secrets=RawParams({}).to_thrift(),
                    output_filename=output_filename,
                )
            )
            self.assertEqual(result.filename, output_filename)
            self.assertEqual(
                [RenderError.from_thrift(e) for e in result.errors],
                [RenderError(I18nMessage.TODO_i18n("bad things"))],
            )
            self.assertEqual(Path(output_filename).read_bytes(), b"")

    def test_fetch_return_uncoerceable_dataframe_is_error(self):
        async def fetch(params):
            return pd.DataFrame({"A": [1, "2"]})  # mixed types -- invalid

        with ExitStack() as ctx:
            output_filename = ctx.enter_context(tempfile.NamedTemporaryFile()).name
            ctx.enter_context(patch.object(module, "fetch", fetch))
            with self.assertRaisesRegex(ValueError, "invalid value"):
                module.fetch_thrift(
                    ttypes.FetchRequest(
                        params=Params({}).to_thrift(),
                        secrets=RawParams({}).to_thrift(),
                        output_filename=output_filename,
                    )
                )

    def test_fetch_raise(self):
        async def fetch(params):
            raise RuntimeError("buggy fetch")

        with ExitStack() as ctx:
            output_filename = ctx.enter_context(tempfile.NamedTemporaryFile()).name
            ctx.enter_context(patch.object(module, "fetch", fetch))
            with self.assertRaisesRegex(RuntimeError, "buggy fetch"):
                module.fetch_thrift(
                    ttypes.FetchRequest(
                        params=Params({}).to_thrift(),
                        secrets=RawParams({}).to_thrift(),
                        output_filename=output_filename,
                    )
                )

    def test_fetch_sync(self):
        def fetch(params):
            return pd.DataFrame({"A": [1, 2, 3]})

        with ExitStack() as ctx:
            output_filename = ctx.enter_context(tempfile.NamedTemporaryFile()).name
            ctx.enter_context(patch.object(module, "fetch", fetch))
            result = module.fetch_thrift(
                ttypes.FetchRequest(
                    params=Params({}).to_thrift(),
                    secrets=RawParams({}).to_thrift(),
                    output_filename=output_filename,
                )
            )
            self.assertEqual(result.filename, output_filename)
            self.assertEqual(result.errors, [])
            arrow_table = pyarrow.parquet.read_table(output_filename, use_threads=False)
            assert_arrow_table_equals(arrow_table, {"A": [1, 2, 3]})
