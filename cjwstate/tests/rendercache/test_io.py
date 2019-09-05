import datetime
import pandas
import pyarrow
from cjwkernel.pandas import types as ptypes  # Pandas types
from cjwkernel import types as atypes  # Arrow types
from cjwkernel.tests.util import arrow_table
from cjwstate import minio
from cjwstate.models import Workflow, WfModule
from cjwstate.models.commands import InitWorkflowCommand
from cjwstate.tests.utils import DbTestCase
from cjwstate.rendercache.io import (
    BUCKET,
    cache_pandas_render_result,
    cache_render_result,
    open_cached_render_result,
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

    def test_cache_pandas_render_result(self):
        result = ptypes.ProcessResult(
            dataframe=pandas.DataFrame({"A": [1]}),
            error="err",
            json={"foo": "bar"},
            quick_fixes=[ptypes.QuickFix("X", "prependModule", ["x", {"a": "b"}])],
            columns=[ptypes.Column("a", ptypes.ColumnType.NUMBER("{:,}"))],
        )

        cache_pandas_render_result(self.workflow, self.wf_module, self.delta.id, result)

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

        # Data comes through loud and clear
        with open_cached_render_result(from_db) as result:
            self.assertEqual(
                result.errors,
                [
                    atypes.RenderError(
                        atypes.I18nMessage("TODO_i18n", ["err"]),
                        [
                            atypes.QuickFix(
                                atypes.I18nMessage("TODO_i18n", ["X"]),
                                atypes.QuickFixAction.PrependStep("x", {"a": "b"}),
                            )
                        ],
                    )
                ],
            )
            self.assertEqual(result.json, {"foo": "bar"})
            with arrow_table(pyarrow.Table.from_pydict({"A": [1]})) as table:
                self.assertEqual(result.table.metadata, table.metadata)
                self.assert_(result.table.table.equals(table.table))

    def test_cache_render_result(self):
        with arrow_table(pyarrow.Table.from_pydict({"A": [1]})) as table:
            result = atypes.RenderResult(
                table,
                [
                    atypes.RenderError(
                        atypes.I18nMessage("e1", [1, "x"]),
                        [
                            atypes.QuickFix(
                                atypes.I18nMessage("q1", []),
                                atypes.QuickFixAction.PrependStep("filter", {"a": "x"}),
                            )
                        ],
                    ),
                    atypes.RenderError(atypes.I18nMessage("e2", []), []),
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
            # `result` is still in scope; so even though its file was deleted,
            # it's still mmapped into an ArrowTable.
            self.assertEqual(result2, result)

    def test_clear(self):
        result = ptypes.ProcessResult(pandas.DataFrame({"a": [1]}))
        cache_pandas_render_result(self.workflow, self.wf_module, self.delta.id, result)
        parquet_key = crr_parquet_key(self.wf_module.cached_render_result)
        clear_cached_render_result_for_wf_module(self.wf_module)

        db_wf_module = WfModule.objects.get(id=self.wf_module.id)
        self.assertIsNone(db_wf_module.cached_render_result)

        self.assertFalse(minio.exists(BUCKET, parquet_key))

    def test_metadata_comes_from_db_columns(self):
        columns = [
            ptypes.Column("A", ptypes.ColumnType.NUMBER(format="{:,d}")),
            ptypes.Column("B", ptypes.ColumnType.DATETIME()),
            ptypes.Column("C", ptypes.ColumnType.TEXT()),
            ptypes.Column("D", ptypes.ColumnType.TEXT()),
        ]
        result = ptypes.ProcessResult(
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
        cache_pandas_render_result(self.workflow, self.wf_module, self.delta.id, result)

        # cache_pandas_render_result() keeps its `result` parameter in memory, so we
        # can avoid disk entirely. Prove it by deleting from disk.
        minio.remove(BUCKET, crr_parquet_key(self.wf_module.cached_render_result))

        # Load _new_ CachedRenderResult -- from DB columns, not memory
        fresh_wf_module = WfModule.objects.get(id=self.wf_module.id)
        cached_result = fresh_wf_module.cached_render_result

        self.assertEqual(cached_result.nrows, 1)
        self.assertEqual(cached_result.columns, columns)
