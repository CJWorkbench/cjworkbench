from server.models import StoredObject
from server.utils import *
from server.tests.utils import *
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone
import pandas as pd
import os
import json

class StoredObjectTests(TestCase):

    def setUp(self):
        self.workflow = create_testdata_workflow()
        self.wfm1 = WfModule.objects.first()
        self.wfm2 = add_new_wf_module(self.workflow, ModuleVersion.objects.first(), 1)  # order = 1
        self.test_data = 'stored data'.encode()
        self.metadata = 'metadataish'

        # Use a more realistic test table with lots of data of different types
        # mock data wasn't finding bugs related to dict-type columns
        fname = os.path.join(settings.BASE_DIR, 'server/tests/test_data/sfpd.json')
        sfpd = json.load(open(fname))
        self.test_table = pd.DataFrame(sfpd)
        sanitize_dataframe(self.test_table)

    def file_contents(self, file_obj):
        file_obj.open(mode='rb')
        data = file_obj.read()
        file_obj.close()
        return data

    def test_store_fetched_table(self):
        so1 = StoredObject.create_table(self.wfm1,
                                        StoredObject.FETCHED_TABLE,
                                        self.test_table,
                                        self.metadata)
        self.assertEqual(so1.type, StoredObject.FETCHED_TABLE)
        self.assertEqual(so1.metadata, self.metadata )
        table2 = so1.get_table()
        self.assertTrue(table2.equals(self.test_table))

    def test_store_cached_table(self):
        so1 = StoredObject.create_table(self.wfm1,
                                        StoredObject.CACHED_TABLE,
                                        self.test_table,
                                        metadata=self.metadata)
        self.assertEqual(so1.type, StoredObject.CACHED_TABLE)
        self.assertEqual(so1.metadata, self.metadata )
        self.assertEqual(so1.size, os.stat(so1.file.name).st_size)
        table2 = so1.get_table()
        self.assertTrue(table2.equals(self.test_table))

    def store_empty_table(self):
        so1 = StoredObject.create_table(self.wfm1,
                                        StoredObject.CACHED_TABLE,
                                        None,
                                        metadata=self.metadata)
        self.assertEqual(so1.type, StoredObject.CACHED_TABLE)
        self.assertEqual(so1.metadata, self.metadata )
        self.assertEqual(so1.size, 0)
        table2 = so1.get_table()
        self.assertTrue(table2.empty)


    def test_nan_storage(self):
        # have previously run into problems serializing / deserializing NaN values
        test_csv = 'Class,M,F\n' \
                   'math,10,12\n' \
                   'english,,7\n' \
                   'history,11,13\n' \
                   'economics,20,20'
        test_table = pd.read_csv(io.StringIO(test_csv))
        test_table_M = pd.DataFrame(test_table['M'])  # need DataFrame ctor otherwise we get series not df

        so = StoredObject.create_table(self.wfm1, StoredObject.FETCHED_TABLE, test_table_M)
        table_out = so.get_table()
        self.assertTrue(table_out.equals(test_table_M))


    def test_create_table_if_different(self):
        so1 = StoredObject.create_table(self.wfm1, StoredObject.FETCHED_TABLE, mock_csv_table)

        so2 = StoredObject.create_table_if_different(self.wfm1, so1, StoredObject.FETCHED_TABLE, mock_csv_table)
        self.assertIsNone(so2)

        so3 = StoredObject.create_table_if_different(self.wfm1, so1, StoredObject.FETCHED_TABLE, mock_csv_table2)
        self.assertIsNotNone(so3)
        table3 = so3.get_table()
        self.assertTrue(table3.equals(mock_csv_table2))

    # Duplicate from one wfm to another, tests the typical WfModule duplication case
    def test_duplicate_table(self):
        so1 = StoredObject.create_table(self.wfm1, StoredObject.FETCHED_TABLE, mock_csv_table)
        so2 = so1.duplicate(self.wfm2)

        # new StoredObject should have same time, same type, same metadata, different file with same contents
        self.assertEqual(so1.stored_at, so2.stored_at)
        self.assertEqual(so1.type, so2.type)
        self.assertEqual(so1.metadata, so2.metadata)
        self.assertNotEqual(so1.file, so2.file)

        self.assertEqual(self.file_contents(so1.file), self.file_contents(so2.file))
        self.assertTrue(so1.get_table().equals(so2.get_table()))

    def test_duplicate_file(self):
        fname = 'myfile.dat'
        content = b'This is everything we are going to store in this file'
        file = default_storage.save(fname, ContentFile(content))
        so1 = StoredObject.objects.create(
            wf_module=self.wfm1,
            type=StoredObject.UPLOADED_FILE,
            stored_at = timezone.now(),
            metadata=self.metadata,
            name=fname,
            size=len(content),
            uuid='XXXXUUID',
            file=file)

        # If it didn't crash, we're good. Not really worth testing Django models here.

        so2 = so1.duplicate(self.wfm2)
        so2.refresh_from_db()

        # new StoredObject should have same time, same type, same metadata, different file with same contents
        self.assertEqual(so1.stored_at, so2.stored_at)
        self.assertEqual(so1.type, so2.type)
        self.assertEqual(so1.metadata, so2.metadata)
        self.assertEqual(so1.name, so2.name)
        self.assertEqual(so1.size, so2.size)
        self.assertEqual(so1.uuid, so2.uuid)
        self.assertNotEqual(so1.file, so2.file)

        data2 = self.file_contents(so2.file)
        self.assertEqual(data2, content)
        self.assertEqual(self.file_contents(so1.file), self.file_contents(so2.file))
