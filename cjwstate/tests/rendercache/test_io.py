import datetime

import numpy as np
import pyarrow as pa
from cjwmodule.arrow.testing import assert_arrow_table_equals, make_column, make_table

from cjwkernel.types import (
    RenderError,
    LoadedRenderResult,
    Column,
    ColumnType,
    I18nMessage,
    QuickFix,
    QuickFixAction,
    TableMetadata,
)
from cjwkernel.tests.util import arrow_table_context, tempfile_context
from cjwstate import s3
from cjwstate.models import Workflow, Step
from cjwstate.tests.utils import DbTestCase
from cjwstate.rendercache.io import (
    BUCKET,
    CorruptCacheError,
    cache_render_result,
    open_cached_render_result,
    clear_cached_render_result_for_step,
    crr_parquet_key,
    read_cached_render_result_slice_as_text,
)


class RendercacheIoTests(DbTestCase):
    def setUp(self):
        super().setUp()
        self.workflow = Workflow.objects.create()
        self.tab = self.workflow.tabs.create(position=0)
        self.step = self.tab.steps.create(
            order=0, slug="step-1", last_relevant_delta_id=1
        )

    def test_cache_render_result(self):
        with arrow_table_context(make_column("A", [1])) as (table_path, table):
            result = LoadedRenderResult(
                path=table_path,
                table=table,
                columns=[Column("A", ColumnType.Number(format="{:,}"))],
                errors=[
                    RenderError(
                        I18nMessage("e1", {"text": "hi"}, None),
                        [
                            QuickFix(
                                I18nMessage("q1", {"var": 2}, None),
                                QuickFixAction.PrependStep("filter", {"a": "x"}),
                            )
                        ],
                    ),
                    RenderError(I18nMessage("e2", {}, None), []),
                ],
                json={"foo": "bar"},
            )
            cache_render_result(self.workflow, self.step, 1, result)

        cached = self.step.cached_render_result
        self.assertEqual(cached.step_id, self.step.id)
        self.assertEqual(cached.delta_id, 1)

        self.assertEqual(
            crr_parquet_key(cached),
            f"wf-{self.workflow.id}/wfm-{self.step.id}/delta-1.dat",
        )

        # Reading completely freshly from the DB should give the same thing
        db_step = Step.objects.get(id=self.step.id)
        from_db = db_step.cached_render_result
        self.assertEqual(from_db, cached)

        with open_cached_render_result(from_db) as result2:
            assert_arrow_table_equals(
                result2.table, make_table(make_column("A", [1], format="{:,}"))
            )
            self.assertEqual(
                result2.columns, [Column("A", ColumnType.Number(format="{:,}"))]
            )

    def test_clear(self):
        with arrow_table_context(make_column("A", [1])) as (path, table):
            result = LoadedRenderResult(
                path=path,
                table=table,
                columns=[Column("A", ColumnType.Number(format="{:,}"))],
                errors=[],
                json={},
            )
            cache_render_result(self.workflow, self.step, 1, result)

        parquet_key = crr_parquet_key(self.step.cached_render_result)
        clear_cached_render_result_for_step(self.step)

        db_step = Step.objects.get(id=self.step.id)
        self.assertIsNone(db_step.cached_render_result)

        self.assertFalse(s3.exists(BUCKET, parquet_key))

    def test_metadata_does_not_require_file_read(self):
        columns = [
            Column("A", ColumnType.Number(format="{:,.2f}")),
            Column("B", ColumnType.Timestamp()),
            Column("C", ColumnType.Text()),
            Column("D", ColumnType.Date("month")),
        ]
        with arrow_table_context(
            make_column("A", [1], format="{:,.2f}"),
            make_column("B", [datetime.datetime(2021, 4, 13)]),
            make_column("C", ["c"]),
            make_column("D", [datetime.date(2021, 4, 1)], unit="month"),
        ) as (path, table):
            result = LoadedRenderResult(
                path=path, table=table, columns=columns, errors=[], json={}
            )
            cache_render_result(self.workflow, self.step, 1, result)
        # Delete from disk entirely, to prove we did not read.
        s3.remove(BUCKET, crr_parquet_key(self.step.cached_render_result))

        # Load _new_ CachedRenderResult -- from DB columns, not memory
        fresh_step = Step.objects.get(id=self.step.id)
        cached_result = fresh_step.cached_render_result

        self.assertEqual(cached_result.table_metadata, TableMetadata(1, columns))

    def test_invalid_parquet_is_corrupt_cache_error(self):
        with arrow_table_context(make_column("A", ["x"])) as (path, table):
            result = LoadedRenderResult(
                path=path,
                table=table,
                columns=[Column("A", ColumnType.Text())],
                errors=[],
                json={},
            )
            cache_render_result(self.workflow, self.step, 1, result)
        crr = self.step.cached_render_result
        s3.put_bytes(BUCKET, crr_parquet_key(crr), b"NOT PARQUET")
        with tempfile_context() as arrow_path:
            with self.assertRaises(CorruptCacheError):
                with open_cached_render_result(crr) as loaded:
                    pass

    def test_read_cached_render_result_slice_as_text_timestamp(self):
        with arrow_table_context(
            make_column("A", [2134213412341232967, None], pa.timestamp("ns"))
        ) as (path, table):
            result = LoadedRenderResult(
                path=path,
                table=table,
                columns=[Column("A", ColumnType.Timestamp())],
                errors=[],
                json={},
            )
            cache_render_result(self.workflow, self.step, 1, result)
        crr = self.step.cached_render_result
        self.assertEqual(
            read_cached_render_result_slice_as_text(crr, "csv", range(2), range(3)),
            "A\n2037-08-18T13:03:32.341232967Z\n",
        )
