import os
import shutil
import unittest
from contextlib import ExitStack  # workaround https://github.com/psf/black/issues/664
from datetime import date, datetime
from pathlib import Path
from typing import Tuple
from unittest.mock import patch

import pandas as pd
import pyarrow as pa
from pandas.testing import assert_frame_equal
from cjwmodule.arrow.testing import assert_arrow_table_equals, make_column, make_table

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
    Params,
    RawParams,
    RenderError,
    RenderResult,
    Tab,
    TabOutput,
    arrow_fetch_result_to_thrift,
    arrow_params_to_thrift,
    arrow_raw_params_to_thrift,
    arrow_tab_to_thrift,
    thrift_fetch_result_to_arrow,
    thrift_raw_params_to_arrow,
    thrift_render_result_to_arrow,
)
from cjwkernel.util import create_tempdir, tempfile_context
from cjwkernel.validate import load_untrusted_arrow_file_with_columns, read_columns


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


class RenderTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.basedir = create_tempdir()
        self.old_cwd = os.getcwd()
        os.chdir(self.basedir)

    def tearDown(self):
        os.chdir(self.old_cwd)
        shutil.rmtree(self.basedir)
        super().tearDown()

    def _test_render(
        self,
        render_fn,
        arrow_table_columns=[],
        arrow_table_filename=None,
        params={},
        tab=Tab("tab-1", "Tab 1"),
        fetch_result=None,
        output_filename=None,
    ):
        with ExitStack() as ctx:
            if arrow_table_filename is None:
                arrow_table_path, _ = ctx.enter_context(
                    arrow_table_context(*arrow_table_columns, dir=self.basedir)
                )
                arrow_table_filename = arrow_table_path.name
            ctx.enter_context(patch.object(module, "render", render_fn))
            if output_filename is None:
                output_filename = ctx.enter_context(
                    tempfile_context(dir=self.basedir)
                ).name
            thrift_result = module.render_thrift(
                ttypes.RenderRequest(
                    basedir=str(self.basedir),
                    input_filename=arrow_table_filename,
                    params=arrow_params_to_thrift(Params(params)),
                    tab=arrow_tab_to_thrift(tab),
                    fetch_result=(
                        arrow_fetch_result_to_thrift(fetch_result)
                        if fetch_result is not None
                        else None
                    ),
                    output_filename=output_filename,
                )
            )
            return thrift_render_result_to_arrow(thrift_result)

    def _test_render_with_output_table(
        self,
        render_fn,
        arrow_table_columns=[],
        arrow_table_filename=None,
        params={},
        tab=Tab("tab-1", "Tab 1"),
        fetch_result=None,
    ) -> Tuple[RenderResult, pa.Table]:
        with tempfile_context(dir=self.basedir) as out_path:
            result = self._test_render(
                render_fn=render_fn,
                arrow_table_columns=arrow_table_columns,
                arrow_table_filename=arrow_table_filename,
                params=params,
                tab=tab,
                fetch_result=fetch_result,
                output_filename=out_path.name,
            )
            if out_path.stat().st_size > 0:
                table, _ = load_untrusted_arrow_file_with_columns(out_path)
            else:
                table = None
            return result, table

    def test_default_render_returns_fetch_result(self):
        # Functionality used by libraryofcongress
        with ExitStack() as ctx:
            input_path, _ = ctx.enter_context(
                arrow_table_context(make_column("A", [1]), dir=self.basedir)
            )
            parquet_filename = Path(
                ctx.enter_context(parquet_file({"A": [2]}, dir=self.basedir)).name
            ).name
            out_filename = ctx.enter_context(tempfile_context(dir=self.basedir)).name
            thrift_result = module.render_thrift(
                ttypes.RenderRequest(
                    basedir=str(self.basedir),
                    input_filename=input_path.name,
                    params={},
                    tab=ttypes.Tab("tab-1", "Tab 1"),
                    fetch_result=ttypes.FetchResult(
                        filename=parquet_filename,
                        errors=[
                            ttypes.RenderError(
                                ttypes.I18nMessage(
                                    "TODO_i18n",
                                    {
                                        "text": ttypes.I18nArgument(
                                            string_value="A warning"
                                        )
                                    },
                                    None,
                                ),
                                [],
                            )
                        ],
                    ),
                    output_filename=out_filename,
                )
            )
            result = thrift_render_result_to_arrow(thrift_result)
            self.assertEqual(
                result, RenderResult([RenderError(TODO_i18n("A warning"))])
            )
            result_table, _ = load_untrusted_arrow_file_with_columns(Path(out_filename))
            assert_arrow_table_equals(result_table, make_table(make_column("A", [2])))

    def test_render_with_tab_name(self):
        def render(table, params, *, tab_name):
            self.assertEqual(tab_name, "Tab X")

        self._test_render(render, tab=Tab("tab-1", "Tab X"))

    @override_settings(MAX_ROWS_PER_TABLE=12)
    def test_render_with_settings(self):
        def render(table, params, *, settings):
            self.assertEqual(settings.MAX_ROWS_PER_TABLE, 12)

        self._test_render(render)

    def test_render_with_no_kwargs(self):
        def render(table, params):
            return table * 2

        result, table = self._test_render_with_output_table(
            render, [make_column("A", [1])]
        )
        self.assertEqual(result, RenderResult())
        assert_arrow_table_equals(table, make_table(make_column("A", [2])))

    def test_render_arrow_table(self):
        # The param name "arrow_table" is a special case
        def render(arrow_table, params, output_path, **kwargs):
            out = pa.table({"A": [2]})
            with pa.ipc.RecordBatchFileWriter(output_path, out.schema) as writer:
                writer.write_table(out)
            # Normally, this file wouldn't be readable by
            # load_untrusted_arrow_file_with_columns(). The module framework
            # must rewrite it to be compatible; that's what we're testing.

        result, table = self._test_render_with_output_table(
            render, [make_column("A", [1])]
        )
        self.assertEqual(result, RenderResult())
        assert_arrow_table_equals(table, make_table(make_column("A", [2])))

    def test_render_arrow_table_zero_byte_output_is_empty(self):
        # The param name "arrow_table" is a special case
        def render(arrow_table, params, output_path, **kwargs):
            output_path.write_bytes(b"")

        with tempfile_context(dir=self.basedir) as out_path:
            result = self._test_render(
                render, [make_column("A", [1])], output_filename=out_path.name
            )
            self.assertEqual(result, RenderResult())
            self.assertEqual(out_path.stat().st_size, 0)

    def test_render_arrow_table_empty_output_table_is_empty(self):
        # The param name "arrow_table" is a special case
        def render(arrow_table, params, output_path, **kwargs):
            out = pa.table({})
            with pa.ipc.RecordBatchFileWriter(output_path, out.schema) as writer:
                writer.write_table(out)

        result, table = self._test_render_with_output_table(
            render, [make_column("A", [1])]
        )
        self.assertEqual(result, RenderResult())
        assert_arrow_table_equals(table, make_table())

    def test_render_arrow_table_errors(self):
        # The param name "arrow_table" is a special case
        def render(arrow_table, params, output_path, **kwargs):
            return [("x", {"a": "b"}, "cjwmodule")]

        result, table = self._test_render_with_output_table(
            render, [make_column("A", [1])]
        )
        self.assertIsNone(table)
        self.assertEqual(
            result,
            RenderResult(
                errors=[RenderError(I18nMessage("x", {"a": "b"}, "cjwmodule"))]
            ),
        )

    @override_settings(MAX_ROWS_PER_TABLE=12)
    def test_render_arrow_table_settings(self):
        def render(arrow_table, params, output_path, *, settings, **kwargs):
            return [("x", {"n": settings.MAX_ROWS_PER_TABLE})]

        result = self._test_render(render, [make_column("A", [1])])
        self.assertEqual(
            result,
            RenderResult(errors=[RenderError(I18nMessage("x", {"n": 12}, None))]),
        )

    def test_render_arrow_table_infer_output_column_formats_from_input(self):
        # The param name "arrow_table" is a special case
        def render(arrow_table, params, output_path, *, columns, **kwargs):
            # Test the "columns" kwarg
            self.assertEqual(
                columns,
                [
                    Column("A", ColumnType.Number("{:,.3f}")),
                    Column("B", ColumnType.Number("{:,.3f}")),
                    Column("C", ColumnType.Number("{:,.3f}")),
                    Column("D", ColumnType.Timestamp()),
                    Column("E", ColumnType.Timestamp()),
                    Column("F", ColumnType.Timestamp()),
                    Column("G", ColumnType.Text()),
                    Column("H", ColumnType.Text()),
                    Column("I", ColumnType.Text()),
                    Column("J", ColumnType.Date(unit="day")),
                    Column("K", ColumnType.Date(unit="week")),
                    Column("L", ColumnType.Text()),
                ],
            )
            table = pa.table(
                {
                    "A": [1],
                    "B": pa.array([datetime(2020, 3, 8)], pa.timestamp("ns")),
                    "C": ["a"],
                    "D": [1],
                    "E": pa.array([datetime(2020, 3, 8)], pa.timestamp("ns")),
                    "F": ["a"],
                    "G": [1],
                    "H": pa.array([datetime(2020, 3, 8)], pa.timestamp("ns")),
                    "I": ["a"],
                    "J": pa.array([date(2021, 4, 1)]),
                    "K": pa.array([date(2021, 4, 12)]),
                    "L": pa.array([date(2021, 4, 1)]),
                }
            )
            schema = table.schema.set(
                table.schema.get_field_index("J"),
                pa.field("J", pa.date32(), metadata={"unit": "month"}),
            )
            with pa.ipc.RecordBatchFileWriter(output_path, schema) as writer:
                writer.write_table(pa.table(table.columns, schema=schema))
            return []

        with arrow_table_context(
            make_column("A", [1], format="{:,.3f}"),
            make_column("B", [1], format="{:,.3f}"),
            make_column("C", [1], format="{:,.3f}"),
            make_column("D", [datetime(2020, 3, 8)]),
            make_column("E", [datetime(2020, 3, 8)]),
            make_column("F", [datetime(2020, 3, 8)]),
            make_column("G", ["a"]),
            make_column("H", ["a"]),
            make_column("I", ["a"]),
            make_column("J", [date(2021, 4, 13)], unit="day"),
            make_column("K", [date(2021, 4, 12)], unit="week"),
            make_column("L", ["a"]),
            dir=self.basedir,
        ) as (arrow_table_path, _):
            result, table = self._test_render_with_output_table(
                render, arrow_table_filename=arrow_table_path.name
            )
            self.assertEqual(
                table,
                make_table(
                    make_column("A", [1], format="{:,.3f}"),  # recalled
                    make_column("B", [datetime(2020, 3, 8)]),
                    make_column("C", ["a"]),
                    make_column("D", [1], format="{:,}"),  # inferred
                    make_column("E", [datetime(2020, 3, 8)]),
                    make_column("F", ["a"]),
                    make_column("G", [1], format="{:,}"),  # inferred
                    make_column("H", [datetime(2020, 3, 8)]),
                    make_column("I", ["a"]),
                    make_column("J", [date(2021, 4, 1)], unit="month"),  # inferred
                    make_column("K", [date(2021, 4, 12)], unit="week"),  # recalled
                    make_column("L", [date(2021, 4, 1)], unit="day"),  # fallback
                ),
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
            result, table = self._test_render_with_output_table(
                render, fetch_result=FetchResult(pf)
            )
            self.assertEqual(result, RenderResult())
            assert_arrow_table_equals(table, make_table(make_column("A", ["fetched"])))

    def test_render_with_non_parquet_fetch_result(self):
        def render(table, params, *, fetch_result):
            return pd.DataFrame({"A": [fetch_result.path.read_text()]})

        with tempfile_context(dir=self.basedir) as tf:
            tf.write_bytes(b"abcd")
            result, table = self._test_render_with_output_table(
                render, fetch_result=FetchResult(tf)
            )
            self.assertEqual(result, RenderResult())
            assert_arrow_table_equals(table, make_table(make_column("A", ["abcd"])))

    def test_render_empty_file_fetch_result_is_parquet(self):
        def render(table, params, *, fetch_result):
            assert_frame_equal(fetch_result.dataframe, pd.DataFrame({}))
            return fetch_result.dataframe

        with tempfile_context(dir=self.basedir) as tf:
            result, table = self._test_render_with_output_table(
                render, fetch_result=FetchResult(tf)
            )
            self.assertEqual(result, RenderResult())
            self.assertIsNone(table)  # no columns: table is written as b""

    def test_render_with_input_columns(self):
        def render(table, params, *, input_columns):
            self.assertEqual(
                input_columns,
                {
                    "A": ptypes.RenderColumn("A", "text", None),
                    "B": ptypes.RenderColumn("B", "number", "{:,.3f}"),
                    "C": ptypes.RenderColumn("C", "timestamp", None),
                },
            )

        with arrow_table_context(
            make_column("A", ["x"]),
            make_column("B", [1], format="{:,.3f}"),
            make_column("C", [datetime.now()]),
            dir=self.basedir,
        ) as (arrow_table_path, _):
            self._test_render(render, arrow_table_filename=arrow_table_path.name)

    def test_render_use_input_columns_as_try_fallback_columns(self):
        def render(table, params, *, input_columns):
            return pd.DataFrame({"A": [1]})

        with arrow_table_context(
            make_column("A", [1], format="{:,.3f}"), dir=self.basedir
        ) as (arrow_table_path, table):
            result, table = self._test_render_with_output_table(
                render, arrow_table_filename=arrow_table_path.name
            )
            self.assertEqual(table, make_table(make_column("A", [1], format="{:,.3f}")))

    def test_render_return_column_formats(self):
        def render(table, params):
            return {
                "dataframe": pd.DataFrame({"A": [1]}),
                "column_formats": {"A": "${:,d}"},
            }

        result, table = self._test_render_with_output_table(render)
        self.assertEqual(result, RenderResult())
        assert_arrow_table_equals(
            table, make_table(make_column("A", [1], format="${:,d}"))
        )

    @override_settings(MAX_ROWS_PER_TABLE=2)
    def test_render_truncate(self):
        def render(table, params):
            return pd.DataFrame({"A": [1, 2, 3]})

        result, table = self._test_render_with_output_table(render)
        assert_arrow_table_equals(table, make_table(make_column("A", [1, 2])))
        self.assertEqual(
            result,
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
            make_column("X", [1], format="{:,d}"),
            make_column("Y", ["y"]),
            dir=self.basedir,
        ) as (path, table):
            self._test_render(
                render,
                params={
                    "tabparam": TabOutput(
                        tab=Tab("tab-1", "Tab 1"), table_filename=path.name
                    )
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
            assert_frame_equal(
                module._parquet_to_pandas(outfile), pd.DataFrame({"A": [1, 2]})
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
