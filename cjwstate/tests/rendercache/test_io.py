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
from cjwstate import minio
from cjwstate.models import Workflow, WfModule
from cjwstate.models.commands import InitWorkflowCommand
from cjwstate.tests.utils import DbTestCase
from cjwstate.rendercache.io import (
    BUCKET,
    CorruptCacheError,
    cache_render_result,
    load_cached_render_result,
    open_cached_render_result,
    clear_cached_render_result_for_wf_module,
    crr_parquet_key,
    read_cached_render_result_pydict,
)


class RendercacheIoTests(DbTestCase):
    def setUp(self):
        super().setUp()
        self.workflow = Workflow.objects.create()
        self.delta = InitWorkflowCommand.create(self.workflow)
        self.tab = self.workflow.tabs.create(position=0)
        self.wf_module = self.tab.wf_modules.create(
            order=0, slug="step-1", last_relevant_delta_id=self.delta.id
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
        cache_render_result(self.workflow, self.wf_module, self.delta.id, result)

        cached = self.wf_module.cached_render_result
        self.assertEqual(cached.wf_module_id, self.wf_module.id)
        self.assertEqual(cached.delta_id, self.delta.id)

        self.assertEqual(
            crr_parquet_key(cached),
            f"wf-{self.workflow.id}/wfm-{self.wf_module.id}/delta-{self.delta.id}.dat",
        )

        # Reading completely freshly from the DB should give the same thing
        db_wf_module = WfModule.objects.get(id=self.wf_module.id)
        from_db = db_wf_module.cached_render_result
        self.assertEqual(from_db, cached)

        with open_cached_render_result(from_db) as result2:
            assert_render_result_equals(result2, result)

    def test_clear(self):
        result = RenderResult(arrow_table({"A": [1]}))
        cache_render_result(self.workflow, self.wf_module, self.delta.id, result)
        parquet_key = crr_parquet_key(self.wf_module.cached_render_result)
        clear_cached_render_result_for_wf_module(self.wf_module)

        db_wf_module = WfModule.objects.get(id=self.wf_module.id)
        self.assertIsNone(db_wf_module.cached_render_result)

        self.assertFalse(minio.exists(BUCKET, parquet_key))

    def test_metadata_comes_from_db_columns(self):
        columns = [
            Column("A", ColumnType.Number(format="{:,.2f}")),
            Column("B", ColumnType.Datetime()),
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
        cache_render_result(self.workflow, self.wf_module, self.delta.id, result)
        # Delete from disk entirely, to prove we did not read.
        minio.remove(BUCKET, crr_parquet_key(self.wf_module.cached_render_result))

        # Load _new_ CachedRenderResult -- from DB columns, not memory
        fresh_wf_module = WfModule.objects.get(id=self.wf_module.id)
        cached_result = fresh_wf_module.cached_render_result

        self.assertEqual(cached_result.table_metadata, TableMetadata(1, columns))

    def test_invalid_parquet_is_corrupt_cache_error(self):
        result = RenderResult(arrow_table({"A": [1]}))
        cache_render_result(self.workflow, self.wf_module, self.delta.id, result)
        crr = self.wf_module.cached_render_result
        minio.put_bytes(BUCKET, crr_parquet_key(crr), b"NOT PARQUET")
        with tempfile_context() as arrow_path:
            with self.assertRaises(CorruptCacheError):
                load_cached_render_result(crr, arrow_path)

    def test_read_cached_render_result_pydict_float_nan_is_none(self):
        result = RenderResult(
            arrow_table(
                {
                    "A": [
                        1.1,
                        # np.nan is DEPRECATED but [2019-12-09] it isn't worth
                        # clearing all caches just to wipe this out.
                        np.nan,
                        # None is the _correct_ way of storing Pandas NaN.
                        # (It's consistent with the way we store int, timestamp
                        # and string. We don't have a special meaning for
                        # np.nan.)
                        None,
                    ],
                    "B": [1, None, None],
                },
                columns=[
                    Column("A", ColumnType.Number(format="{:,.2f}")),
                    Column("B", ColumnType.Number(format="{:,d}")),
                ],
            )
        )
        cache_render_result(self.workflow, self.wf_module, self.delta.id, result)
        crr = self.wf_module.cached_render_result
        self.assertEqual(
            read_cached_render_result_pydict(crr, range(2), range(3)),
            {"A": [1.1, None, None], "B": [1, None, None]},
        )

    def test_read_cached_render_result_pydict_datetime(self):
        result = RenderResult(
            arrow_table(
                {"A": pa.array([2134213412341232967, None], pa.timestamp("ns"))},
                columns=[Column("A", ColumnType.Datetime())],
            )
        )
        cache_render_result(self.workflow, self.wf_module, self.delta.id, result)
        crr = self.wf_module.cached_render_result
        self.assertEqual(
            read_cached_render_result_pydict(crr, range(2), range(3)),
            # We lose the "967" (nanosecond digits) because Python dates only
            # store microseconds.
            #
            # [2019-12-09] it would be great to enforce the rule, "all dates
            # must be in 'us' resolution." But Pandas enforces the rule, "all
            # dates must be in 'ns' resolution. Ouch.
            {"A": [datetime.datetime(2037, 8, 18, 13, 3, 32, 341232), None]},
        )
