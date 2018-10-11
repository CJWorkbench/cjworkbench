import os.path
import datetime
import pandas
from server.tests.utils import DbTestCase
from server.models import Workflow, WfModule
from server.models.Commands import InitWorkflowCommand
from server.modules.types import Column, ProcessResult, QuickFix


class CachedRenderResultTests(DbTestCase):
    def setUp(self):
        super().setUp()
        self.workflow = Workflow.objects.create()
        self.wf_module = self.workflow.wf_modules.create(order=0)

    def test_none(self):
        self.assertIsNone(self.wf_module.get_cached_render_result())

    def test_assign_and_save(self):
        result = ProcessResult(
            pandas.DataFrame({'a': [1]}), 'err',
            json={'foo': 'bar'},
            quick_fixes=[QuickFix('X', 'prependModule', 'x')]
        )
        self.wf_module.cache_render_result(2, result)

        cached = self.wf_module.get_cached_render_result()
        self.assertEqual(cached.workflow_id, self.workflow.id)
        self.assertEqual(cached.wf_module_id, self.wf_module.id)
        self.assertEqual(cached.delta_id, 2)
        self.assertEqual(cached.result, result)

        self.assertTrue(os.path.isfile(cached.parquet_path))

        self.wf_module.save()
        db_wf_module = WfModule.objects.get(id=self.wf_module.id)
        from_db = db_wf_module.get_cached_render_result()
        self.assertEqual(from_db.workflow_id, self.workflow.id)
        self.assertEqual(from_db.wf_module_id, self.wf_module.id)
        self.assertEqual(cached.delta_id, 2)
        self.assertEqual(from_db.result, result)

    def test_set_to_empty(self):
        result = ProcessResult(pandas.DataFrame({'a': [1]}))
        self.wf_module.cache_render_result(2, result)
        self.wf_module.save()

        parquet_path = self.wf_module.get_cached_render_result().parquet_path

        db_wf_module = WfModule.objects.get(id=self.wf_module.id)
        db_wf_module.cache_render_result(3, None)
        db_wf_module.save()

        db_wf_module = WfModule.objects.get(id=self.wf_module.id)
        self.assertIsNone(db_wf_module.get_cached_render_result())
        self.assertFalse(os.path.isfile(parquet_path))

    def test_metadata_comes_from_memory_when_available(self):
        result = ProcessResult(pandas.DataFrame({
            'A': [1],  # int64
            'B': [datetime.datetime(2018, 8, 20)],  # datetime64[ns]
            'C': ['foo'],  # str
        }))
        result.dataframe['D'] = pandas.Series(['cat'], dtype='category')
        cached_result = self.wf_module.cache_render_result(2, result)
        # cache_render_result() keeps its `result` parameter in memory, so we
        # can avoid disk entirely.
        #
        # This is great for the render pipeline: it never reads from the file
        # it writes, as it renders all modules sequentially.
        os.unlink(cached_result.parquet_path)
        self.assertFalse(cached_result._result is None)

        self.assertEqual(cached_result.result, result)

        self.assertEqual(len(cached_result), 1)
        self.assertEqual(cached_result.column_names, ['A', 'B', 'C', 'D'])
        self.assertEqual(cached_result.column_types,
                         ['number', 'datetime', 'text', 'text'])
        self.assertEqual(cached_result.columns, [
            Column('A', 'number'),
            Column('B', 'datetime'),
            Column('C', 'text'),
            Column('D', 'text'),
        ])

    def test_metadata_does_not_read_whole_file_from_disk(self):
        result = ProcessResult(pandas.DataFrame({
            'A': [1],  # int64
            'B': [datetime.datetime(2018, 8, 20)],  # datetime64[ns]
            'C': ['foo'],  # str
        }))
        result.dataframe['D'] = pandas.Series(['cat'], dtype='category')
        self.wf_module.cache_render_result(2, result)
        self.wf_module.save()

        cached_result = self.wf_module.get_cached_render_result()
        cached_result.parquet_file  # read header
        os.unlink(cached_result.parquet_path)
        self.assertEqual(len(cached_result), 1)
        self.assertEqual(cached_result.column_names, ['A', 'B', 'C', 'D'])
        self.assertEqual(cached_result.column_types,
                         ['number', 'datetime', 'text', 'text'])
        self.assertEqual(cached_result.columns, [
            Column('A', 'number'),
            Column('B', 'datetime'),
            Column('C', 'text'),
            Column('D', 'text'),
        ])

        with self.assertRaises(FileNotFoundError):
            # Prove that we didn't read from the file
            self.assertIsNone(cached_result.result)

    def test_delete_wfmodule(self):
        result = ProcessResult(pandas.DataFrame({'a': [1]}))
        self.wf_module.cache_render_result(2, result)
        self.wf_module.save()

        parquet_path = self.wf_module.get_cached_render_result().parquet_path
        self.wf_module.delete()
        self.assertFalse(os.path.isfile(parquet_path))

    def test_delete_after_moved_from_workflow_to_delta(self):
        # When we move the WfModule out of a workflow (so it's only part of
        # a Delta), we should clear the cache. Otherwise there isn't a clear
        # time for cache-clearing: a WfModule without a Workflow doesn't have
        # the path information it needs to save the cached_render_result.
        result = ProcessResult(pandas.DataFrame({'a': [1]}))
        self.wf_module.cache_render_result(2, result)
        self.wf_module.save()

        parquet_path = self.wf_module.get_cached_render_result().parquet_path

        db_wf_module = WfModule.objects.get(id=self.wf_module.id)
        db_wf_module.workflow = None
        db_wf_module.save()

        db_wf_module = WfModule.objects.get(id=self.wf_module.id)
        db_wf_module.delete()

        self.assertIsNone(db_wf_module.get_cached_render_result())
        self.assertFalse(os.path.isfile(parquet_path))

    def test_assign_none_over_none(self):
        self.wf_module.workflow = None
        self.wf_module.save()
        self.wf_module.cache_render_result(None, None)

        self.assertIsNone(self.wf_module.get_cached_render_result())

    def test_duplicate_copies_fresh_cache(self):
        # The cache's filename depends on workflow_id and wf_module_id.
        # Duplicating it would need more complex code :).
        result = ProcessResult(pandas.DataFrame({'a': [1]}))
        self.wf_module.last_relevant_delta_id = 2
        self.wf_module.cache_render_result(2, result)
        self.wf_module.save()

        workflow2 = Workflow.objects.create()
        InitWorkflowCommand.create(workflow2)
        dup = self.wf_module.duplicate(workflow2)

        dup_cached_result = dup.get_cached_render_result()
        self.assertIsNotNone(dup_cached_result)
        self.assertEqual(dup_cached_result.result, result)

    def test_duplicate_ignores_stale_cache(self):
        # The cache's filename depends on workflow_id and wf_module_id.
        # Duplicating it would need more complex code :).
        result = ProcessResult(pandas.DataFrame({'a': [1]}))
        self.wf_module.last_relevant_delta_id = 1
        self.wf_module.cache_render_result(2, result)
        self.wf_module.save()

        workflow2 = Workflow.objects.create()
        InitWorkflowCommand.create(workflow2)
        dup = self.wf_module.duplicate(workflow2)

        dup_cached_result = dup.get_cached_render_result()
        self.assertIsNone(dup_cached_result)
