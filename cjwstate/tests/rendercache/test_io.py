import datetime
import numpy as np
import pyarrow as pa
from cjwkernel.tests.util import arrow_table, assert_render_result_equals
from cjwkernel.types import (
    RenderError,
    RenderResult,
    Column,
    ColumnType,
    I18nMessage,
    QuickFix,
    QuickFixAction,
    TableMetadata,
)
from cjwkernel.tests.util import tempfile_context
from cjwstate import s3
from cjwstate.models import Workflow, Step
from cjwstate.tests.utils import DbTestCase
from cjwstate.rendercache.io import (
    BUCKET,
    CorruptCacheError,
    cache_render_result,
    load_cached_render_result,
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
        result = RenderResult(
            arrow_table({"A": [1]}),
            [
                RenderError(
                    I18nMessage("e1", [1, "x"]),
                    [
                        QuickFix(
                            I18nMessage("q1", []),
                            QuickFixAction.PrependStep("filter", {"a": "x"}),
                        )
                    ],
                ),
                RenderError(I18nMessage("e2", []), []),
            ],
            {"foo": "bar"},
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
            assert_render_result_equals(result2, result)

    def test_clear(self):
        result = RenderResult(arrow_table({"A": [1]}))
        cache_render_result(self.workflow, self.step, 1, result)
        parquet_key = crr_parquet_key(self.step.cached_render_result)
        clear_cached_render_result_for_step(self.step)

        db_step = Step.objects.get(id=self.step.id)
        self.assertIsNone(db_step.cached_render_result)

        self.assertFalse(s3.exists(BUCKET, parquet_key))

    def test_metadata_comes_from_db_columns(self):
        columns = [
            Column("A", ColumnType.Number(format="{:,.2f}")),
            Column("B", ColumnType.Timestamp()),
            Column("C", ColumnType.Text()),
        ]
        result = RenderResult(
            arrow_table(
                {
                    "A": [1],
                    "B": pa.array([datetime.datetime.now()], pa.timestamp("ns")),
                    "C": ["x"],
                },
                columns=columns,
            )
        )
        cache_render_result(self.workflow, self.step, 1, result)
        # Delete from disk entirely, to prove we did not read.
        s3.remove(BUCKET, crr_parquet_key(self.step.cached_render_result))

        # Load _new_ CachedRenderResult -- from DB columns, not memory
        fresh_step = Step.objects.get(id=self.step.id)
        cached_result = fresh_step.cached_render_result

        self.assertEqual(cached_result.table_metadata, TableMetadata(1, columns))

    def test_invalid_parquet_is_corrupt_cache_error(self):
        result = RenderResult(arrow_table({"A": [1]}))
        cache_render_result(self.workflow, self.step, 1, result)
        crr = self.step.cached_render_result
        s3.put_bytes(BUCKET, crr_parquet_key(crr), b"NOT PARQUET")
        with tempfile_context() as arrow_path:
            with self.assertRaises(CorruptCacheError):
                load_cached_render_result(crr, arrow_path)

    def test_read_cached_render_result_slice_as_text_timestamp(self):
        result = RenderResult(
            arrow_table(
                {"A": pa.array([2134213412341232967, None], pa.timestamp("ns"))},
                columns=[Column("A", ColumnType.Timestamp())],
            )
        )
        cache_render_result(self.workflow, self.step, 1, result)
        crr = self.step.cached_render_result
        self.assertEqual(
            read_cached_render_result_slice_as_text(crr, "csv", range(2), range(3)),
            "A\n2037-08-18T13:03:32.341232967Z\n",
        )
