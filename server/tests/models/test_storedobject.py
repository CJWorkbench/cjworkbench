import os
import json
import tempfile
from django.conf import settings
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from server.models import StoredObject, Workflow
from server.sanitizedataframe import sanitize_dataframe
from server.tests.utils import DbTestCase
from django.test import override_settings


# don't clutter media directory with our tests (and don't accidentally succeed
# because of files there)
@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class StoredObjectTests(DbTestCase):
    def setUp(self):
        super().setUp()

        self.workflow = Workflow.objects.create()
        tab = self.workflow.tabs.create(position=0)
        self.wfm1 = tab.wf_modules.create(order=0)
        self.metadata = 'metadataish'

    def file_contents(self, file_obj):
        file_obj.open(mode='rb')
        data = file_obj.read()
        file_obj.close()
        return data

    def test_store_some_random_table(self):
        # Use a more realistic test table with lots of data of different types
        # mock data wasn't finding bugs related to dict-type columns
        fname = os.path.join(settings.BASE_DIR,
                             'server/tests/test_data/sfpd.json')
        with open(fname) as f:
            sfpd = json.load(f)
        self.test_table = pd.DataFrame(sfpd)
        sanitize_dataframe(self.test_table)

        so1 = StoredObject.create_table(self.wfm1,
                                        self.test_table,
                                        self.metadata)
        self.assertEqual(so1.metadata, self.metadata)
        table2 = so1.get_table()
        self.assertTrue(table2.equals(self.test_table))

    def test_store_empty_table(self):
        so1 = StoredObject.create_table(self.wfm1,
                                        pd.DataFrame(),
                                        metadata=self.metadata)
        self.assertEqual(so1.metadata, self.metadata)
        table2 = so1.get_table()
        self.assertTrue(table2.empty)

    def test_load_obsolete_stored_empty_table(self):
        """
        Load a table from before 2018-11-09.

        Previously, we'd special-case "empty" DataFrames. No more.
        """
        so1 = StoredObject.objects.create(
            wf_module=self.wfm1,
            metadata=self.metadata,
            file=None,
            size=0,
            hash=0
        )

        table = so1.get_table()
        assert_frame_equal(table, pd.DataFrame())

    def test_nan_storage(self):
        # have previously run into problems serializing/deserializing NaN
        table = pd.DataFrame({
            'M': [10, np.nan, 11, 20],
        }, dtype=np.float64)

        so = StoredObject.create_table(self.wfm1, table)
        assert_frame_equal(so.get_table(), table)

    def test_create_table_if_different(self):
        df1 = pd.DataFrame({'A': [1]})
        df2 = pd.DataFrame({'A': [2]})

        so1 = StoredObject.create_table(self.wfm1, df1)

        so2 = StoredObject.create_table_if_different(self.wfm1, so1, df1)
        self.assertIsNone(so2)

        so3 = StoredObject.create_table_if_different(self.wfm1, so1, df2)
        self.assertIsNotNone(so3)

        table3 = so3.get_table()
        assert_frame_equal(table3, df2)

    def test_duplicate_table(self):
        table = pd.DataFrame({'A': [1]})

        self.wfm2 = self.wfm1.tab.wf_modules.create(order=1)
        so1 = StoredObject.create_table(self.wfm1, table)
        so2 = so1.duplicate(self.wfm2)

        # new StoredObject should have same time, same metadata,
        # different file with same contents
        self.assertEqual(so1.stored_at, so2.stored_at)
        self.assertEqual(so1.metadata, so2.metadata)
        self.assertNotEqual(so1.file, so2.file)

        self.assertEqual(self.file_contents(so1.file),
                         self.file_contents(so2.file))

    def test_read_file_missing(self):
        so = StoredObject(file='hello', size=10)
        assert_frame_equal(so.get_table(), pd.DataFrame())

    def test_read_file_fastparquet_issue_375(self):
        so = StoredObject(
            file=os.path.join(os.path.dirname(__file__), '..', 'test_data',
                              'fastparquet-issue-375-snappy.par'),
            size=10
        )
        assert_frame_equal(so.get_table(), pd.DataFrame())
