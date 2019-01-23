import os.path
import datetime
import pandas
from server.tests.utils import DbTestCase
from server.models import Workflow, WfModule
from server.models.commands import InitWorkflowCommand
from server.modules.types import Column, ProcessResult, QuickFix
from server import minio


class CachedRenderResultTests(DbTestCase):
    def setUp(self):
        super().setUp()
        self.workflow = Workflow.objects.create()
        delta = InitWorkflowCommand.create(self.workflow)
        self.tab = self.workflow.tabs.create(position=0)
        self.wf_module = self.tab.wf_modules.create(
            order=0,
            last_relevant_delta_id=delta.id
        )

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
        self.assertEqual(cached.wf_module_id, self.wf_module.id)
        self.assertEqual(cached.delta_id, 2)
        self.assertEqual(cached.result, result)

        self.assertEqual(
            cached.parquet_key,
            (
                f'wf-{self.workflow.id}/wfm-{self.wf_module.id}'
                f'/delta-2.dat'
            )
        )

        self.wf_module.save()
        db_wf_module = WfModule.objects.get(id=self.wf_module.id)
        from_db = db_wf_module.get_cached_render_result()
        self.assertEqual(from_db.wf_module_id, self.wf_module.id)
        self.assertEqual(cached.delta_id, 2)
        self.assertEqual(from_db.result, result)

    def test_set_to_empty(self):
        result = ProcessResult(pandas.DataFrame({'a': [1]}))
        self.wf_module.cache_render_result(2, result)
        self.wf_module.save()

        parquet_key = self.wf_module.get_cached_render_result().parquet_key

        db_wf_module = WfModule.objects.get(id=self.wf_module.id)
        db_wf_module.cache_render_result(3, None)
        db_wf_module.save()

        db_wf_module = WfModule.objects.get(id=self.wf_module.id)
        self.assertIsNone(db_wf_module.get_cached_render_result())
        with self.assertRaises(minio.error.NoSuchKey):
            minio.minio_client.get_object(minio.CachedRenderResultsBucket,
                                          parquet_key)

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
        minio.minio_client.remove_object(minio.CachedRenderResultsBucket,
                                         cached_result.parquet_key)
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

    # To test this, we'd need a >5MB file (since our Parquet chunk size is
    # 5MB). Or we'd need to make the chunk size configurable. Not worth the
    # effort.
    #def test_metadata_does_not_read_whole_file_from_disk(self):
    #    result = ProcessResult(pandas.DataFrame({
    #        'A': [1],  # int64
    #        'B': [datetime.datetime(2018, 8, 20)],  # datetime64[ns]
    #        'C': ['foo'],  # str
    #    }))
    #    result.dataframe['D'] = pandas.Series(['cat'], dtype='category')
    #    self.wf_module.cache_render_result(2, result)
    #    self.wf_module.save()

    #    cached_result = self.wf_module.get_cached_render_result()
    #    cached_result.parquet_file  # read header
    #    minio.minio_client.remove_object(minio.CachedRenderResultsBucket,
    #                                     cached_result.parquet_key)
    #    self.assertEqual(len(cached_result), 1)
    #    self.assertEqual(cached_result.column_names, ['A', 'B', 'C', 'D'])
    #    self.assertEqual(cached_result.column_types,
    #                     ['number', 'datetime', 'text', 'text'])
    #    self.assertEqual(cached_result.columns, [
    #        Column('A', 'number'),
    #        Column('B', 'datetime'),
    #        Column('C', 'text'),
    #        Column('D', 'text'),
    #    ])

    #    with self.assertRaises(FileNotFoundError):
    #        # Prove that we didn't read from the file
    #        self.assertIsNone(cached_result.result)

    def test_delete_wfmodule(self):
        result = ProcessResult(pandas.DataFrame({'a': [1]}))
        self.wf_module.cache_render_result(2, result)
        self.wf_module.save()

        parquet_key = self.wf_module.get_cached_render_result().parquet_key
        self.wf_module.delete()
        with self.assertRaises(minio.error.NoSuchKey):
            minio.minio_client.get_object(minio.CachedRenderResultsBucket,
                                          parquet_key)
        # Note: we _don't_ test soft-delete. Soft-deleted modules aren't
        # extremely common, so it's not like we'll be preserving terabytes of
        # unused cached render results.
        #
        # If this assumption is wrong, by all means wipe the cache on
        # soft-delete.

    def test_assign_none_over_none(self):
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
        tab2 = workflow2.tabs.create(position=0)
        InitWorkflowCommand.create(workflow2)
        dup = self.wf_module.duplicate(tab2)

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
        tab2 = workflow2.tabs.create(position=0)
        InitWorkflowCommand.create(workflow2)
        dup = self.wf_module.duplicate(tab2)

        dup_cached_result = dup.get_cached_render_result()
        self.assertIsNone(dup_cached_result)
