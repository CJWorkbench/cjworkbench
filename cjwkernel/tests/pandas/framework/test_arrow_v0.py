import unittest
from datetime import date, datetime

import pyarrow as pa
from cjwmodule.arrow.testing import assert_arrow_table_equals, make_column, make_table
from cjwmodule.spec.paramschema import ParamSchema

from cjwkernel.tests.util import override_settings
from cjwkernel.types import (
    Column,
    ColumnType,
    I18nMessage,
    RenderError,
    RenderResult,
    UploadedFile,
)
from cjwkernel.validate import load_untrusted_arrow_file_with_columns
from .util import ModuleTestEnv


class RenderTests(unittest.TestCase):
    def test_render_arrow_table(self):
        # The param name "arrow_table" is a special case
        def render(arrow_table, params, output_path, **kwargs):
            out = pa.table({"A": [2]})
            with pa.ipc.RecordBatchFileWriter(output_path, out.schema) as writer:
                writer.write_table(out)
            # Normally, this file wouldn't be readable by
            # load_untrusted_arrow_file_with_columns(). The module framework
            # must rewrite it to be compatible; that's what we're testing.

        with ModuleTestEnv(render=render) as env:
            outcome = env.call_render(
                table=make_table(make_column("A", [1])), params={}
            )
            self.assertEqual(outcome.result, RenderResult())
            assert_arrow_table_equals(
                load_untrusted_arrow_file_with_columns(outcome.path)[0],
                make_table(make_column("A", [2])),
            )

    def test_render_arrow_table_zero_byte_output_is_empty(self):
        # The param name "arrow_table" is a special case
        def render(arrow_table, params, output_path, **kwargs):
            output_path.write_bytes(b"")

        with ModuleTestEnv(render=render) as env:
            outcome = env.call_render(make_table(), {})
            self.assertEqual(outcome.result, RenderResult())
            self.assertEqual(outcome.path.stat().st_size, 0)

    def test_render_arrow_table_empty_output_table_is_empty(self):
        # The param name "arrow_table" is a special case
        def render(arrow_table, params, output_path, **kwargs):
            out = pa.table({})
            with pa.ipc.RecordBatchFileWriter(output_path, out.schema) as writer:
                writer.write_table(out)

        with ModuleTestEnv(render=render) as env:
            outcome = env.call_render(make_table(), {})
            self.assertEqual(outcome.result, RenderResult())
            self.assertEqual(outcome.read_table(), make_table())

    def test_render_arrow_table_errors(self):
        # The param name "arrow_table" is a special case
        def render(arrow_table, params, output_path, **kwargs):
            return [("x", {"a": "b"}, "cjwmodule")]

        with ModuleTestEnv(render=render) as env:
            outcome = env.call_render(make_table(), {})
            self.assertEqual(
                outcome.result,
                RenderResult(
                    errors=[RenderError(I18nMessage("x", {"a": "b"}, "cjwmodule"))]
                ),
            )
            self.assertEqual(outcome.path.stat().st_size, 0)

    @override_settings(MAX_ROWS_PER_TABLE=12)
    def test_render_arrow_table_settings(self):
        def render(arrow_table, params, output_path, *, settings, **kwargs):
            self.assertEqual(settings.MAX_ROWS_PER_TABLE, 12)

        with ModuleTestEnv(render=render) as env:
            env.call_render(make_table(), {})

    def test_render_arrow_table_infer_output_column_formats(self):
        def render(arrow_table, params, output_path, *, columns, **kwargs):
            out = pa.table({"A": [1], "B": [date(2021, 4, 1)]})
            with pa.ipc.RecordBatchFileWriter(output_path, out.schema) as writer:
                writer.write_table(out)

        with ModuleTestEnv(render=render) as env:
            outcome = env.call_render(make_table(), {})
            assert_arrow_table_equals(
                outcome.read_table(),
                make_table(
                    make_column("A", [1], format="{:,}"),
                    make_column("B", [date(2021, 4, 1)], unit="day"),
                ),
            )

    def test_render_arrow_table_infer_output_column_formats_from_input(self):
        # The param name "arrow_table" is a special case
        def render(arrow_table, params, output_path, *, columns, **kwargs):
            # Test the "columns" kwarg
            #
            # TODO nix this! The only module that uses it is `converttotext`.
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

        with ModuleTestEnv(render=render) as env:
            outcome = env.call_render(
                make_table(
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
                ),
                {},
            )
            self.assertEqual(
                outcome.read_table(),
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

    def test_render_file_param(self):
        def render(arrow_table, params, output_path, *args, **kwargs):
            self.assertEqual(params["file"].read_bytes(), b"hi")

        param_schema = ParamSchema.Dict({"file": ParamSchema.File()})
        with ModuleTestEnv(param_schema=param_schema, render=render) as env:
            filename = "839526fa-1adb-4eec-9d29-f5b4d2fbba30_x.tar.gz"
            (env.basedir / filename).write_bytes(b"hi")
            env.call_render(
                make_table(),
                {"file": "839526fa-1adb-4eec-9d29-f5b4d2fbba30"},
                uploaded_files={
                    "839526fa-1adb-4eec-9d29-f5b4d2fbba30": UploadedFile(
                        "x.tar.gz", filename, datetime.now()
                    )
                },
            )

    def test_render_empty_file_param(self):
        def render(arrow_table, params, output_path, *args, **kwargs):
            self.assertIsNone(params["file"])

        param_schema = ParamSchema.Dict({"file": ParamSchema.File()})
        with ModuleTestEnv(param_schema=param_schema, render=render) as env:
            env.call_render(make_table(), {"file": None})
