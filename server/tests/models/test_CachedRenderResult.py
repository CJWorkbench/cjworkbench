import os.path
import datetime
import pandas
from server.tests.utils import DbTestCase
from server.models import Workflow, WfModule
from server.modules.types import ProcessResult


class CachedRenderResultTests(DbTestCase):
    def setUp(self):
        super().setUp()
        self.workflow = Workflow.objects.create()
        self.wf_module = self.workflow.wf_modules.create(order=0)

    def test_none(self):
        self.assertIsNone(self.wf_module.get_cached_render_result())

    def test_assign_and_save(self):
        result = ProcessResult(pandas.DataFrame({'a': [1]}), 'err')
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

    def test_column_names_and_types_do_not_read_file(self):
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
        self.assertEqual(cached_result.column_names, ['A', 'B', 'C', 'D'])
        self.assertEqual(cached_result.column_types,
                         ['number', 'datetime', 'text', 'text'])

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

    def test_duplicate_does_not_copy_cache(self):
        # The cache's filename depends on workflow_id and wf_module_id.
        # Duplicating it would need more complex code :).
        result = ProcessResult(pandas.DataFrame({'a': [1]}))
        self.wf_module.cache_render_result(2, result)
        self.wf_module.save()

        workflow2 = Workflow.objects.create()
        dup = self.wf_module.duplicate(workflow2)
        self.assertIsNone(dup.get_cached_render_result())
