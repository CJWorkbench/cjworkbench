import datetime
import pandas
from cjwkernel.pandas.types import Column, ColumnType, ProcessResult, QuickFix
from cjwstate import minio
from cjwstate.models import Workflow, WfModule
from cjwstate.models.commands import InitWorkflowCommand
from cjwstate.tests.utils import DbTestCase
from cjwstate.rendercache.io import (
    BUCKET,
    cache_render_result,
    read_cached_render_result,
    clear_cached_render_result_for_wf_module,
    crr_parquet_key,
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

    def test_assign_and_save(self):
        result = ProcessResult(
            dataframe=pandas.DataFrame({"a": [1]}),
            error="err",
            json={"foo": "bar"},
            quick_fixes=[QuickFix("X", "prependModule", ["x"])],
            columns=[Column("a", ColumnType.NUMBER("{:,d}"))],
        )

        cache_render_result(self.workflow, self.wf_module, self.delta.id, result)

        cached = self.wf_module.cached_render_result
        self.assertEqual(cached.wf_module_id, self.wf_module.id)
        self.assertEqual(cached.delta_id, self.delta.id)
        self.assertEqual(read_cached_render_result(cached), result)

        self.assertEqual(
            crr_parquet_key(cached),
            f"wf-{self.workflow.id}/wfm-{self.wf_module.id}/delta-{self.delta.id}.dat",
        )

        # Reading completely freshly from the DB should give the same thing
        db_wf_module = WfModule.objects.get(id=self.wf_module.id)
        from_db = db_wf_module.cached_render_result
        self.assertEqual(from_db.wf_module_id, self.wf_module.id)
        self.assertEqual(from_db.delta_id, self.delta.id)
        self.assertEqual(read_cached_render_result(from_db), result)

    def test_clear(self):
        result = ProcessResult(pandas.DataFrame({"a": [1]}))
        cache_render_result(self.workflow, self.wf_module, self.delta.id, result)
        parquet_key = crr_parquet_key(self.wf_module.cached_render_result)
        clear_cached_render_result_for_wf_module(self.wf_module)

        db_wf_module = WfModule.objects.get(id=self.wf_module.id)
        self.assertIsNone(db_wf_module.cached_render_result)

        self.assertFalse(minio.exists(BUCKET, parquet_key))

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
        cache_render_result(self.workflow, self.wf_module, self.delta.id, result)

        # cache_render_result() keeps its `result` parameter in memory, so we
        # can avoid disk entirely. Prove it by deleting from disk.
        minio.remove(BUCKET, crr_parquet_key(self.wf_module.cached_render_result))

        # Load _new_ CachedRenderResult -- from DB columns, not memory
        fresh_wf_module = WfModule.objects.get(id=self.wf_module.id)
        cached_result = fresh_wf_module.cached_render_result

        self.assertEqual(cached_result.nrows, 1)
        self.assertEqual(cached_result.columns, columns)
