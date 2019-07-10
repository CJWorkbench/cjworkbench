import datetime
import pandas
from cjworkbench.types import Column, ColumnType, ProcessResult, QuickFix
from server import minio
from server.models import Workflow, WfModule
from server.models.commands import InitWorkflowCommand
from server.tests.utils import DbTestCase


class CachedRenderResultTests(DbTestCase):
    def setUp(self):
        super().setUp()
        self.workflow = Workflow.objects.create()
        self.delta = InitWorkflowCommand.create(self.workflow)
        self.tab = self.workflow.tabs.create(position=0)
        self.wf_module = self.tab.wf_modules.create(
            order=0, last_relevant_delta_id=self.delta.id
        )

    def test_none(self):
        self.assertIsNone(self.wf_module.cached_render_result)

    def test_assign_and_save(self):
        result = ProcessResult(
            dataframe=pandas.DataFrame({"a": [1]}),
            error="err",
            json={"foo": "bar"},
            quick_fixes=[QuickFix("X", "prependModule", ["x"])],
            columns=[Column("a", ColumnType.NUMBER("{:,d}"))],
        )
        self.wf_module.cache_render_result(self.delta.id, result)

        cached = self.wf_module.cached_render_result
        self.assertEqual(cached.wf_module_id, self.wf_module.id)
        self.assertEqual(cached.delta_id, self.delta.id)
        self.assertEqual(cached.result, result)

        self.assertEqual(
            cached.parquet_key,
            (
                f"wf-{self.workflow.id}/wfm-{self.wf_module.id}"
                f"/delta-{self.delta.id}.dat"
            ),
        )

        db_wf_module = WfModule.objects.get(id=self.wf_module.id)
        from_db = db_wf_module.cached_render_result
        self.assertEqual(from_db.wf_module_id, self.wf_module.id)
        self.assertEqual(cached.delta_id, self.delta.id)
        self.assertEqual(from_db.result, result)

    def test_set_to_empty(self):
        result = ProcessResult(pandas.DataFrame({"a": [1]}))
        self.wf_module.cache_render_result(self.delta.id, result)
        parquet_key = self.wf_module.cached_render_result.parquet_key

        db_wf_module = WfModule.objects.get(id=self.wf_module.id)
        db_wf_module.clear_cached_render_result()
        self.assertIsNone(db_wf_module.cached_render_result)

        db_wf_module.refresh_from_db()
        self.assertIsNone(db_wf_module.cached_render_result)

        self.assertFalse(minio.exists(minio.CachedRenderResultsBucket, parquet_key))

    def test_result_and_metadata_come_from_memory_when_available(self):
        columns = [
            Column("A", ColumnType.NUMBER(format="{:,d}")),
            Column("B", ColumnType.DATETIME()),
            Column("C", ColumnType.TEXT()),
            Column("D", ColumnType.TEXT()),
        ]
        result = ProcessResult(
            dataframe=pandas.DataFrame(
                {
                    "A": [1],  # int64
                    "B": [datetime.datetime(2018, 8, 20)],  # datetime64[ns]
                    "C": ["foo"],  # str
                    "D": pandas.Series(["cat"], dtype="category"),
                }
            ),
            columns=columns,
        )
        cached_result = self.wf_module.cache_render_result(self.delta.id, result)

        # cache_render_result() keeps its `result` parameter in memory, so we
        # can avoid disk entirely. Prove it by deleting from disk.
        minio.remove(minio.CachedRenderResultsBucket, cached_result.parquet_key)
        self.assertFalse(cached_result._result is None)

        self.assertEqual(cached_result.result, result)
        self.assertEqual(cached_result.nrows, 1)
        self.assertEqual(cached_result.columns, columns)

    def test_metadata_comes_from_db_columns(self):
        columns = [
            Column("A", ColumnType.NUMBER(format="{:,d}")),
            Column("B", ColumnType.DATETIME()),
            Column("C", ColumnType.TEXT()),
            Column("D", ColumnType.TEXT()),
        ]
        result = ProcessResult(
            dataframe=pandas.DataFrame(
                {
                    "A": [1],  # int64
                    "B": [datetime.datetime(2018, 8, 20)],  # datetime64[ns]
                    "C": ["foo"],  # str
                    "D": pandas.Series(["cat"], dtype="category"),
                }
            ),
            columns=columns,
        )
        cached_result = self.wf_module.cache_render_result(self.delta.id, result)

        # cache_render_result() keeps its `result` parameter in memory, so we
        # can avoid disk entirely. Prove it by deleting from disk.
        minio.remove(minio.CachedRenderResultsBucket, cached_result.parquet_key)

        # Load _new_ CachedRenderResult -- from DB columns, not memory
        fresh_wf_module = WfModule.objects.get(id=self.wf_module.id)
        cached_result = fresh_wf_module.cached_render_result
        self.assertFalse(hasattr(cached_result, "_result"))

        self.assertEqual(cached_result.nrows, 1)
        self.assertEqual(cached_result.columns, columns)

    def test_delete_wfmodule(self):
        result = ProcessResult(pandas.DataFrame({"a": [1]}))
        self.wf_module.cache_render_result(self.delta.id, result)

        parquet_key = self.wf_module.cached_render_result.parquet_key
        self.wf_module.delete()
        self.assertFalse(minio.exists(minio.CachedRenderResultsBucket, parquet_key))
        # Note: we _don't_ test soft-delete. Soft-deleted modules aren't
        # extremely common, so it's not like we'll be preserving terabytes of
        # unused cached render results.
        #
        # If this assumption is wrong, by all means wipe the cache on
        # soft-delete.

    def test_assign_none_over_none(self):
        self.wf_module.clear_cached_render_result()
        self.assertIsNone(self.wf_module.cached_render_result)

    def test_duplicate_copies_fresh_cache(self):
        # The cache's filename depends on workflow_id and wf_module_id.
        # Duplicating it would need more complex code :).
        result = ProcessResult(pandas.DataFrame({"a": [1]}))
        self.wf_module.cache_render_result(self.delta.id, result)

        workflow2 = Workflow.objects.create()
        tab2 = workflow2.tabs.create(position=0)
        InitWorkflowCommand.create(workflow2)
        dup = self.wf_module.duplicate(tab2)

        dup_cached_result = dup.cached_render_result
        self.assertIsNotNone(dup_cached_result)
        self.assertEqual(dup_cached_result.result, result)

    def test_duplicate_ignores_stale_cache(self):
        # The cache's filename depends on workflow_id and wf_module_id.
        # Duplicating it would need more complex code :).
        result = ProcessResult(pandas.DataFrame({"a": [1]}))
        self.wf_module.cache_render_result(self.delta.id, result)
        # Now simulate a new delta that hasn't been rendered
        self.wf_module.last_relevant_delta_id += 1
        self.wf_module.save(update_fields=["last_relevant_delta_id"])

        workflow2 = Workflow.objects.create()
        tab2 = workflow2.tabs.create(position=0)
        InitWorkflowCommand.create(workflow2)
        dup = self.wf_module.duplicate(tab2)

        dup_cached_result = dup.cached_render_result
        self.assertIsNone(dup_cached_result)
